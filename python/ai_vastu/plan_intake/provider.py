from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx

from ai_vastu.architectural_intelligence.providers.schema_utils import (
    sanitize_gemini_schema,
)
from ai_vastu.gemini_http import post_json_with_retry

from .cad import convert_dwg_to_dxf, summarize_dxf
from .errors import PlanIntakeConfigurationError, PlanIntakeProviderError
from .models import (
    PlanEnvelopeObservation,
    PlanObservationSource,
    PlanOrientationObservation,
    PlanRecognitionDraft,
    PlanReferenceKind,
)


@dataclass(frozen=True, slots=True)
class PlanReferenceBlob:
    filename: str
    content_type: str
    kind: PlanReferenceKind
    data: bytes


@dataclass(frozen=True, slots=True)
class PlanRecognitionInput:
    project_id: UUID
    intake_id: UUID
    prompt: str
    references: tuple[PlanReferenceBlob, ...]


class PlanRecognitionProvider(Protocol):
    name: str

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft: ...


_SYSTEM = """You interpret existing Indian residential floor plans for a Vastu
and architectural planning application.

Your job is PLAN RECOGNITION, not authoritative CAD drafting.

Recognize:
- plot/envelope dimensions only when explicitly written or present in CAD units;
- rooms and labels;
- approximate room centroids relative to the plan boundary;
- North arrow / true-North orientation;
- road side / entrance direction when explicitly visible;
- useful plan observations, questions and uncertainty.

CRITICAL:
- Never invent missing dimensions.
- Never derive exact metric dimensions only from pixels.
- Never infer road_side or entrance_facing merely from parking, driveway,
  setbacks, gates, circulation, or apparent access. Only set them when
  explicitly marked or unambiguously evidenced in the supplied plan.
- If road side or entrance facing is not explicit, leave it null and ask
  the user to confirm it.
- For image/PDF observations, set requires_confirmation=true.
- For CAD data with unknown units, dimensions remain unconfirmed.
- centroid_x_basis_points and centroid_y_basis_points are normalized 0..10000
  coordinates within the visible plot/envelope, with 0,0 at drawing lower-left.
- north_rotation_deg uses 0 when drawing +Y is true North, increasing clockwise.
- Use canonical room types such as living, dining, kitchen, puja, bedroom,
  master_bedroom, common_toilet, attached_toilet, staircase, parking, store,
  utility, balcony, courtyard.
- Do not claim Vastu compliance. Vastu scoring is deterministic downstream.
- Return only the supplied JSON schema.
"""


def _inline_part(content_type: str, data: bytes) -> dict[str, Any]:
    return {
        "inlineData": {
            "mimeType": content_type,
            "data": base64.b64encode(data).decode("ascii"),
        }
    }


def _extract_text(result: dict[str, Any]) -> str:
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise PlanIntakeProviderError("Gemini plan recognition returned no candidates.")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise PlanIntakeProviderError("Unexpected Gemini plan recognition candidate.")
    content = candidate.get("content")
    if not isinstance(content, dict):
        raise PlanIntakeProviderError("Gemini plan recognition returned no content.")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise PlanIntakeProviderError("Gemini plan recognition returned no parts.")
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    raise PlanIntakeProviderError("Gemini plan recognition returned no text.")


class GeminiPlanRecognitionProvider:
    name = "gemini"
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(cls) -> GeminiPlanRecognitionProvider:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise PlanIntakeConfigurationError("GEMINI_API_KEY is required for plan recognition.")
        model = os.getenv(
            "AI_VASTU_PLAN_RECOGNITION_MODEL",
            os.getenv("AI_VASTU_GEMINI_MODEL", "gemini-3.1-flash-lite"),
        ).strip()
        if not model:
            raise PlanIntakeConfigurationError("AI_VASTU_PLAN_RECOGNITION_MODEL must not be blank.")
        return cls(api_key, model)

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        parts: list[dict[str, Any]] = [
            {
                "text": (
                    f"{_SYSTEM}\n\nCLIENT CONTEXT:\n{request.prompt}\n\n"
                    "Analyze every supplied plan reference together."
                )
            }
        ]
        reference_names: list[str] = []
        cad_warnings: list[str] = []

        for reference in request.references:
            reference_names.append(reference.filename)
            if reference.kind in {PlanReferenceKind.IMAGE, PlanReferenceKind.PDF}:
                parts.append(_inline_part(reference.content_type, reference.data))
                continue
            if reference.kind is PlanReferenceKind.DXF:
                parts.append(
                    {
                        "text": (
                            f"\nREFERENCE {reference.filename} (DXF):\n"
                            f"{summarize_dxf(reference.data)}"
                        )
                    }
                )
                continue
            if reference.kind is PlanReferenceKind.DWG:
                try:
                    dxf = convert_dwg_to_dxf(reference.data)
                    summary = summarize_dxf(dxf)
                    parts.append(
                        {
                            "text": (
                                f"\nREFERENCE {reference.filename} "
                                f"(DWG converted to DXF):\n{summary}"
                            )
                        }
                    )
                except PlanIntakeConfigurationError as exc:
                    cad_warnings.append(str(exc))
                    parts.append(
                        {
                            "text": (
                                f"\nREFERENCE {reference.filename}: DWG file was "
                                "uploaded but no DWG-to-DXF backend is configured. "
                                "Do not invent geometry from this file."
                            )
                        }
                    )

        schema = sanitize_gemini_schema(PlanRecognitionDraft.model_json_schema())
        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema,
            },
        }

        try:
            with httpx.Client(
                base_url=self.API_BASE,
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                timeout=120.0,
                transport=self._transport,
            ) as client:
                response = post_json_with_retry(
                    client,
                    f"/models/{self._model}:generateContent",
                    json_payload=payload,
                )
            result = response.json()
            if not isinstance(result, dict):
                raise PlanIntakeProviderError("Unexpected Gemini response object.")
            parsed = json.loads(_extract_text(result))
            if not isinstance(parsed, dict):
                raise PlanIntakeProviderError(
                    "Gemini plan recognition structured output was not an object."
                )
        except PlanIntakeProviderError:
            raise
        except Exception as exc:
            raise PlanIntakeProviderError(f"Gemini plan recognition failed: {exc}") from exc

        parsed.update(
            {
                "project_id": str(request.project_id),
                "intake_id": str(request.intake_id),
                "provider": self.name,
                "model": self._model,
                "reference_names": reference_names,
                "content_hash": None,
            }
        )
        if cad_warnings:
            existing = parsed.get("warnings")
            warnings = list(existing) if isinstance(existing, list) else []
            warnings.extend(cad_warnings)
            parsed["warnings"] = warnings

        try:
            return PlanRecognitionDraft.model_validate_json(json.dumps(parsed)).with_content_hash()
        except Exception as exc:
            raise PlanIntakeProviderError(
                f"Gemini plan recognition output failed validation: {exc}"
            ) from exc


class FixturePlanRecognitionProvider:
    name = "fixture"

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        return PlanRecognitionDraft(
            project_id=request.project_id,
            intake_id=request.intake_id,
            provider=self.name,
            model=None,
            reference_names=tuple(item.filename for item in request.references),
            envelope=PlanEnvelopeObservation(
                geometry_type="RECTANGLE",
                width_mm=9144,
                depth_mm=15240,
                built_up_area_mm2=9144 * 15240,
                confidence=0.95,
                source=PlanObservationSource.MODEL_INFERENCE,
                requires_confirmation=True,
                evidence=("fixture 30x50 ft equivalent envelope",),
            ),
            orientation=PlanOrientationObservation(
                north_rotation_deg=0.0,
                confidence=0.95,
                source=PlanObservationSource.MODEL_INFERENCE,
                requires_confirmation=True,
                evidence=("fixture north-up plan",),
            ),
            rooms=(),
            observations=("Fixture provider does not infer room geometry.",),
            questions=("Confirm the extracted plot dimensions and North.",),
            warnings=(),
        ).with_content_hash()
