from __future__ import annotations

import json
from typing import Any

from ai_vastu.media_validation_adapter import (
    PlanRasterNormalizationError,
    normalize_nvidia_plan_raster,
)
from ai_vastu.nvidia_nim_http import (
    NvidiaNimClient,
    NvidiaNimConfigurationError,
    NvidiaNimModelPolicy,
    NvidiaNimRequestError,
    image_url_part,
    schema_instruction,
)
from ai_vastu.pdf_render_adapter import (
    PdfiumPageRenderer,
    PdfPageRenderer,
    PdfRenderError,
)

from .cad import convert_dwg_to_dxf, summarize_dxf
from .errors import PlanIntakeConfigurationError, PlanIntakeProviderError
from .models import PlanRecognitionDraft, PlanReferenceKind
from .provider import PlanRecognitionInput, PlanRecognitionProvider

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
- For every visual observation, set requires_confirmation=true.
- For CAD data with unknown units, dimensions remain unconfirmed.
- centroid_x_basis_points and centroid_y_basis_points are normalized 0..10000
  coordinates within the visible plot/envelope, with 0,0 at drawing lower-left.
- north_rotation_deg uses 0 when drawing +Y is true North, increasing clockwise.
- Use canonical room types such as living, dining, kitchen, puja, bedroom,
  master_bedroom, common_toilet, attached_toilet, staircase, parking, store,
  utility, balcony, courtyard.
- Do not claim Vastu compliance. Vastu scoring is deterministic downstream.
- Return JSON only, without Markdown fences or commentary.
"""


class NvidiaNimPlanRecognitionProvider:
    name = "nvidia_nim"

    def __init__(
        self,
        *,
        client: NvidiaNimClient,
        policy: NvidiaNimModelPolicy,
        pdf_renderer: PdfPageRenderer | None = None,
    ) -> None:
        policy.validate()
        self._client = client
        self._policy = policy
        self._pdf_renderer = pdf_renderer or PdfiumPageRenderer()

    @classmethod
    def from_environment(cls) -> NvidiaNimPlanRecognitionProvider:
        try:
            return cls(
                client=NvidiaNimClient.from_environment(),
                policy=NvidiaNimModelPolicy.from_environment(),
            )
        except NvidiaNimConfigurationError as exc:
            raise PlanIntakeConfigurationError(str(exc)) from exc

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "CLIENT CONTEXT:\n"
                    + request.prompt
                    + "\n\nAnalyze every supplied plan reference together."
                    + " PDF page images are locally rendered and retain their page labels.\n\n"
                    + schema_instruction(PlanRecognitionDraft.model_json_schema())
                ),
            }
        ]
        reference_names: list[str] = []
        warnings: list[str] = []

        for reference in request.references:
            reference_names.append(reference.filename)
            if reference.kind is PlanReferenceKind.IMAGE:
                try:
                    raster = normalize_nvidia_plan_raster(
                        reference.content_type,
                        reference.data,
                    )
                except PlanRasterNormalizationError as exc:
                    raise PlanIntakeProviderError() from exc
                self._append_image(content, raster.content_type, raster.data)
                continue
            if reference.kind is PlanReferenceKind.PDF:
                try:
                    pages = self._pdf_renderer.render(
                        filename=reference.filename,
                        data=reference.data,
                    )
                except PdfRenderError as exc:
                    raise PlanIntakeProviderError(str(exc)) from exc
                for page in pages:
                    content.append(
                        {
                            "type": "text",
                            "text": f"REFERENCE {page.filename} (locally rendered PDF page):",
                        }
                    )
                    self._append_image(content, page.content_type, page.data)
                warnings.append(
                    f"{reference.filename}: PDF was rendered locally into {len(pages)} "
                    "bounded PNG page image(s); observations require confirmation."
                )
                continue
            if reference.kind is PlanReferenceKind.DXF:
                content.append(
                    {
                        "type": "text",
                        "text": (
                            f"REFERENCE {reference.filename} (DXF semantic summary):\n"
                            f"{summarize_dxf(reference.data)}"
                        ),
                    }
                )
                continue
            if reference.kind is PlanReferenceKind.DWG:
                try:
                    dxf = convert_dwg_to_dxf(reference.data)
                    content.append(
                        {
                            "type": "text",
                            "text": (
                                f"REFERENCE {reference.filename} "
                                "(DWG converted to DXF semantic summary):\n"
                                f"{summarize_dxf(dxf)}"
                            ),
                        }
                    )
                except PlanIntakeConfigurationError as exc:
                    warnings.append(str(exc))
                    content.append(
                        {
                            "type": "text",
                            "text": (
                                f"REFERENCE {reference.filename}: DWG was supplied but no "
                                "DWG-to-DXF backend is configured. Do not invent geometry."
                            ),
                        }
                    )

        def validate(parsed: dict[str, Any], model: str) -> PlanRecognitionDraft:
            payload = dict(parsed)
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
                    {"role": "user", "content": content},
                ),
                models=self._policy.vision_chain,
                validator=validate,
                temperature=0.1,
                max_tokens=4096,
                disable_thinking=True,
            )
        except NvidiaNimRequestError as exc:
            raise PlanIntakeProviderError(exc.category) from exc

    @staticmethod
    def _append_image(
        content: list[dict[str, Any]], content_type: str, data: bytes
    ) -> None:
        try:
            content.append(image_url_part(content_type, data))
        except ValueError as exc:
            raise PlanIntakeProviderError(str(exc)) from exc


def build_nvidia_nim_plan_provider_for_test(
    *,
    client: NvidiaNimClient,
    policy: NvidiaNimModelPolicy,
    pdf_renderer: PdfPageRenderer | None = None,
) -> PlanRecognitionProvider:
    return NvidiaNimPlanRecognitionProvider(
        client=client,
        policy=policy,
        pdf_renderer=pdf_renderer,
    )
