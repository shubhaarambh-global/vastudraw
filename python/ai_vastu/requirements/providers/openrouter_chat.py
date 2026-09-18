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
from ai_vastu.requirements.models import RequirementDraft
from ai_vastu.requirements.providers.base import InterpretationInput


class OpenRouterRequirementsConfigurationError(RuntimeError):
    pass


_SYSTEM = """You are the requirements interpreter for an Indian residential
architectural planning system.

Extract planning requirements from the user's prompt and attached reference files.

CRITICAL BOUNDARY:
- You do not draw authoritative geometry.
- You do not invent missing exact dimensions.
- Values inferred visually from images/PDFs must use source=image/pdf or
  source=model_inference and require confirmation.
- Do not assume property-facing direction equals road side.
- Do not assume road side equals true North.
- Preserve ambiguity in questions/warnings.
- Return JSON only.
"""


class OpenRouterRequirementsProvider:
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
    def from_environment(cls) -> OpenRouterRequirementsProvider:
        try:
            return cls(
                client=OpenRouterClient.from_environment(),
                policy=OpenRouterModelPolicy.from_environment(),
            )
        except OpenRouterConfigurationError as exc:
            raise OpenRouterRequirementsConfigurationError(str(exc)) from exc

    def interpret(self, request: InterpretationInput) -> RequirementDraft:
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Project ID: "
                    + str(request.project_id)
                    + "\n\nClient brief:\n"
                    + request.prompt
                    + "\n\n"
                    + schema_instruction(RequirementDraft.model_json_schema())
                ),
            }
        ]
        has_visual_input = False
        has_pdf = False

        for asset in request.references:
            if asset.content_type in {"image/jpeg", "image/png", "image/webp"}:
                content.append(image_url_part(asset.content_type, asset.data))
                has_visual_input = True
            elif asset.content_type == "application/pdf":
                content.append(pdf_file_part(asset.filename, asset.data))
                has_visual_input = True
                has_pdf = True

        models = self._policy.vision_chain if has_visual_input else self._policy.reasoning_chain

        def validate(parsed: dict[str, Any], model: str) -> RequirementDraft:
            payload = dict(parsed)
            # Application identity is authoritative, never model authority.
            payload.update(
                {
                    "draft_id": str(request.draft_id),
                    "user_id": str(request.user_id),
                    "project_id": str(request.project_id),
                    "prompt": request.prompt,
                    "reference_names": [item.filename for item in request.references],
                    "provider": self.name,
                    "model": model,
                }
            )
            return RequirementDraft.model_validate(payload)

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": content},
                ),
                models=models,
                validator=validate,
                temperature=0.1,
                plugins=FREE_PDF_PLUGIN if has_pdf else (),
            )
        except OpenRouterRequestError as exc:
            raise RuntimeError(f"OpenRouter requirements interpretation failed: {exc}") from exc


def build_openrouter_requirements_provider_for_test(
    *,
    api_key: str,
    transport: httpx.BaseTransport,
) -> OpenRouterRequirementsProvider:
    return OpenRouterRequirementsProvider(
        client=OpenRouterClient(api_key=api_key, transport=transport),
        policy=OpenRouterModelPolicy(),
    )
