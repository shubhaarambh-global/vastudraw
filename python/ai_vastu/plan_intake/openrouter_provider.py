from __future__ import annotations

from typing import Any

import httpx

from ai_vastu.openrouter_http import (
    FREE_PDF_PLUGIN,
    OpenRouterClient,
    OpenRouterConfigurationError,
    OpenRouterModelPolicy,
    OpenRouterRequestError,
    image_url_part,
    pdf_file_part,
    schema_instruction,
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
- For image/PDF observations, set requires_confirmation=true.
- For CAD data with unknown units, dimensions remain unconfirmed.
- centroid_x_basis_points and centroid_y_basis_points are normalized 0..10000
  coordinates within the visible plot/envelope, with 0,0 at drawing lower-left.
- north_rotation_deg uses 0 when drawing +Y is true North, increasing clockwise.
- Use canonical room types such as living, dining, kitchen, puja, bedroom,
  master_bedroom, common_toilet, attached_toilet, staircase, parking, store,
  utility, balcony, courtyard.
- Do not claim Vastu compliance. Vastu scoring is deterministic downstream.
- Return JSON only.
"""


class OpenRouterPlanRecognitionProvider:
    name = "openrouter"

    def __init__(
        self,
        *,
        client: OpenRouterClient,
        policy: OpenRouterModelPolicy,
    ) -> None:
        policy.validate()
        self._client = client
        self._policy = policy

    @classmethod
    def from_environment(cls) -> OpenRouterPlanRecognitionProvider:
        try:
            return cls(
                client=OpenRouterClient.from_environment(),
                policy=OpenRouterModelPolicy.from_environment(),
            )
        except OpenRouterConfigurationError as exc:
            raise PlanIntakeConfigurationError(str(exc)) from exc

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "CLIENT CONTEXT:\n"
                    + request.prompt
                    + "\n\nAnalyze every supplied plan reference together.\n\n"
                    + schema_instruction(PlanRecognitionDraft.model_json_schema())
                ),
            }
        ]
        reference_names: list[str] = []
        cad_warnings: list[str] = []
        has_pdf = False

        for reference in request.references:
            reference_names.append(reference.filename)
            if reference.kind is PlanReferenceKind.IMAGE:
                try:
                    content.append(image_url_part(reference.content_type, reference.data))
                except ValueError as exc:
                    raise PlanIntakeProviderError(str(exc)) from exc
                continue

            if reference.kind is PlanReferenceKind.PDF:
                content.append(pdf_file_part(reference.filename, reference.data))
                has_pdf = True
                cad_warnings.append(
                    f"{reference.filename}: OpenRouter PDF parsing is pinned to the free "
                    "Cloudflare parser. If this is a scanned/image-only plan and visual "
                    "detail is incomplete, upload the relevant sheet as JPG/PNG."
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
                    cad_warnings.append(str(exc))
                    content.append(
                        {
                            "type": "text",
                            "text": (
                                f"REFERENCE {reference.filename}: DWG was supplied but "
                                "no DWG-to-DXF backend is configured. Do not invent geometry."
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
            if cad_warnings:
                raw_warnings = payload.get("warnings")
                warnings = (
                    list(raw_warnings)
                    if isinstance(raw_warnings, (list, tuple))
                    else []
                )
                warnings.extend(cad_warnings)
                payload["warnings"] = warnings
            return PlanRecognitionDraft.model_validate(payload).with_content_hash()

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": content},
                ),
                models=self._policy.vision_chain,
                validator=validate,
                temperature=0.1,
                plugins=FREE_PDF_PLUGIN if has_pdf else (),
            )
        except OpenRouterRequestError as exc:
            raise PlanIntakeProviderError(
                f"OpenRouter plan recognition failed: {exc}"
            ) from exc


def build_openrouter_plan_provider_for_test(
    *,
    api_key: str,
    transport: httpx.BaseTransport,
) -> PlanRecognitionProvider:
    return OpenRouterPlanRecognitionProvider(
        client=OpenRouterClient(api_key=api_key, transport=transport),
        policy=OpenRouterModelPolicy(),
    )
