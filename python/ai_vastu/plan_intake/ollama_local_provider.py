from __future__ import annotations

import base64
import json
from typing import Any

from ai_vastu.media_validation_adapter import (
    PlanRasterNormalizationError,
    validate_ollama_plan_raster,
)
from ai_vastu.ollama_local_http import (
    OllamaLocalClient,
    OllamaLocalConfigurationError,
)
from ai_vastu.pdf_render_adapter import (
    PdfiumPageRenderer,
    PdfPageRenderer,
    PdfRenderError,
)
from ai_vastu.provider_runtime import ProviderRuntimeError

from .cad import convert_dwg_to_dxf, summarize_dxf
from .errors import PlanIntakeConfigurationError, PlanIntakeProviderError
from .models import PlanObservationSource, PlanRecognitionDraft, PlanReferenceKind
from .provider import PlanRecognitionInput

MAX_OLLAMA_PLAN_IMAGES = 8
MAX_OLLAMA_PLAN_IMAGE_BYTES = 32 * 1024 * 1024

_SYSTEM = """You interpret existing Indian residential floor plans for a Vastu
and architectural planning application.

Your job is PLAN RECOGNITION, not authoritative CAD drafting.

Recognize:
- plot/envelope dimensions only when explicitly written or present in CAD units;
- rooms and labels;
- approximate room centroids relative to the plan boundary;
- North arrow / true-North orientation;
- road side / entrance direction only when explicitly visible;
- useful plan observations, questions and uncertainty.

CRITICAL:
- Never invent missing dimensions or derive exact metric dimensions from pixels.
- Never infer road or entrance direction from parking, driveway, gates, or access.
- Every model observation requires user confirmation.
- CAD data with unknown units remains unconfirmed.
- Centroids are normalized 0..10000 within the visible envelope.
- north_rotation_deg is 0 when drawing +Y is true North, increasing clockwise.
- Do not claim Vastu compliance; deterministic downstream rules remain authoritative.
- Return one strict JSON object only, without Markdown or commentary.
"""


class OllamaLocalPlanRecognitionProvider:
    name = "ollama_local"

    def __init__(
        self,
        *,
        client: OllamaLocalClient,
        pdf_renderer: PdfPageRenderer | None = None,
    ) -> None:
        self._client = client
        self._pdf_renderer = pdf_renderer or PdfiumPageRenderer()

    @classmethod
    def from_environment(cls) -> OllamaLocalPlanRecognitionProvider:
        try:
            return cls(client=OllamaLocalClient.from_environment())
        except OllamaLocalConfigurationError as exc:
            raise PlanIntakeConfigurationError(
                "Local Ollama plan recognition is not configured."
            ) from exc

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        text_parts = [
            "CLIENT CONTEXT:\n"
            + request.prompt
            + "\n\nAnalyze every supplied plan reference together. "
            "PDF pages are locally rendered and listed in image order."
        ]
        images: list[str] = []
        total_image_bytes = 0
        reference_names: list[str] = []
        warnings: list[str] = []

        def append_image(*, label: str, content_type: str, data: bytes) -> None:
            nonlocal total_image_bytes
            if len(images) >= MAX_OLLAMA_PLAN_IMAGES:
                raise PlanIntakeProviderError()
            total_image_bytes += len(data)
            if total_image_bytes > MAX_OLLAMA_PLAN_IMAGE_BYTES:
                raise PlanIntakeProviderError()
            text_parts.append(f"IMAGE {len(images) + 1}: {label}")
            images.append(base64.b64encode(data).decode("ascii"))

        for reference in request.references:
            reference_names.append(reference.filename)
            if reference.kind is PlanReferenceKind.IMAGE:
                try:
                    raster = validate_ollama_plan_raster(
                        reference.content_type,
                        reference.data,
                    )
                except PlanRasterNormalizationError as exc:
                    raise PlanIntakeProviderError() from exc
                append_image(
                    label=reference.filename,
                    content_type=raster.content_type,
                    data=raster.data,
                )
                continue
            if reference.kind is PlanReferenceKind.PDF:
                try:
                    pages = self._pdf_renderer.render(
                        filename=reference.filename,
                        data=reference.data,
                    )
                except PdfRenderError as exc:
                    raise PlanIntakeProviderError() from exc
                for page in pages:
                    if page.content_type != "image/png" or not page.data.startswith(
                        b"\x89PNG\r\n\x1a\n"
                    ):
                        raise PlanIntakeProviderError()
                    append_image(
                        label=f"{page.filename} (locally rendered PDF page)",
                        content_type=page.content_type,
                        data=page.data,
                    )
                warnings.append(
                    f"{reference.filename}: PDF was rendered locally into {len(pages)} "
                    "bounded PNG page image(s); observations require confirmation."
                )
                continue
            if reference.kind is PlanReferenceKind.DXF:
                text_parts.append(
                    f"REFERENCE {reference.filename} (DXF semantic summary):\n"
                    f"{summarize_dxf(reference.data)}"
                )
                continue
            if reference.kind is PlanReferenceKind.DWG:
                try:
                    dxf = convert_dwg_to_dxf(reference.data)
                    text_parts.append(
                        f"REFERENCE {reference.filename} "
                        f"(DWG converted to DXF semantic summary):\n{summarize_dxf(dxf)}"
                    )
                except PlanIntakeConfigurationError as exc:
                    warnings.append(str(exc))
                    text_parts.append(
                        f"REFERENCE {reference.filename}: DWG was supplied but no "
                        "DWG-to-DXF backend is configured. Do not invent geometry."
                    )

        user_message: dict[str, Any] = {
            "role": "user",
            "content": "\n\n".join(text_parts),
        }
        if images:
            user_message["images"] = images

        def observation(value: object) -> None:
            if not isinstance(value, dict):
                return
            value["requires_confirmation"] = True
            value["source"] = PlanObservationSource.MODEL_INFERENCE.value

        def validate(parsed: dict[str, Any], model: str) -> PlanRecognitionDraft:
            payload = dict(parsed)
            observation(payload.get("envelope"))
            observation(payload.get("orientation"))
            rooms = payload.get("rooms")
            if isinstance(rooms, list):
                for room in rooms:
                    observation(room)
            payload.update(
                {
                    "schema_version": "26B.5.1",
                    "project_id": str(request.project_id),
                    "intake_id": str(request.intake_id),
                    "provider": self.name,
                    "model": model,
                    "reference_names": reference_names,
                    "content_hash": None,
                }
            )
            if warnings:
                raw_warnings = payload.get("warnings")
                merged = list(raw_warnings) if isinstance(raw_warnings, (list, tuple)) else []
                merged.extend(warnings)
                payload["warnings"] = merged
            return PlanRecognitionDraft.model_validate_json(
                json.dumps(payload)
            ).with_content_hash()

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    user_message,
                ),
                schema=PlanRecognitionDraft.model_json_schema(),
                validator=validate,
                max_tokens=4096,
            )
        except ProviderRuntimeError as exc:
            raise PlanIntakeProviderError(exc.category) from exc
