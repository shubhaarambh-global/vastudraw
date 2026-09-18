from __future__ import annotations

import json
from typing import Any

import httpx

from ai_vastu.openrouter_http import (
    OpenRouterClient,
    OpenRouterConfigurationError,
    OpenRouterModelPolicy,
    OpenRouterRequestError,
    schema_instruction,
)

from ..errors import VastuReasoningConfigurationError
from ..models import VastuReasoningProfile
from .base import VastuReasoningInput

_SYSTEM = """You are the Vastu reasoning layer for an Indian residential
planning system.

You are NOT allowed to invent new Vastu rules. You may reason only over the
source-backed rule catalog supplied by the application.

Your task is contextual interpretation:
- decide whether a catalog rule is applicable to the confirmed program,
- classify its practical importance,
- classify how flexible the rule should be in this project,
- optionally reduce or increase its soft weight within the catalog policy,
- explain conflicts or source disagreement.

CRITICAL POLICY:
- Vastu is a SOFT design influence only.
- Never turn a Vastu principle into a hard geometry constraint.
- Never override safety, statutory requirements, client must-haves, usable room
  dimensions, circulation, accessibility, structure, or deterministic geometry validation.
- Do not change preferred/secondary/avoid sectors from the catalog.
- Do not invent rule IDs.
- Return exactly one reasoning entry for EVERY catalog rule, even when
  the correct applicability is NOT_APPLICABLE.
- Some catalog rules are marked reasoning_adjustable=false. Return their catalog
  default importance/flexibility unchanged.
- Source disagreement must remain visible.
- A rule may be NEGLIGIBLE, LOW, MODERATE, HIGH, or CORE while still remaining soft.
- Return JSON only.
"""


class OpenRouterVastuReasoningProvider:
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
    def from_environment(cls) -> OpenRouterVastuReasoningProvider:
        try:
            return cls(
                client=OpenRouterClient.from_environment(),
                policy=OpenRouterModelPolicy.from_environment(),
            )
        except OpenRouterConfigurationError as exc:
            raise VastuReasoningConfigurationError(str(exc)) from exc

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile:
        user_text = json.dumps(
            {
                "original_client_brief": request.original_prompt,
                "confirmed_requirements": request.confirmed.model_dump(mode="json"),
                "soft_vastu_catalog": request.catalog.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        user_text += "\n\n" + schema_instruction(VastuReasoningProfile.model_json_schema())

        def validate(parsed: dict[str, Any], model: str) -> VastuReasoningProfile:
            payload = dict(parsed)
            payload.update(
                {
                    "schema_version": "26B.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": model,
                    # Application-owned normalization replaces these with the selected mode.
                    "influence_mode": "balanced",
                    "architecture_weight_basis_points": 5000,
                    "vastu_weight_basis_points": 5000,
                    "content_hash": None,
                }
            )
            return VastuReasoningProfile.model_validate(payload).with_content_hash()

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_text},
                ),
                models=self._policy.reasoning_chain,
                validator=validate,
                temperature=0.15,
            )
        except OpenRouterRequestError as exc:
            raise RuntimeError(f"OpenRouter Vastu reasoning failed: {exc}") from exc


def build_openrouter_vastu_provider_for_test(
    *,
    api_key: str,
    transport: httpx.BaseTransport,
) -> OpenRouterVastuReasoningProvider:
    return OpenRouterVastuReasoningProvider(
        client=OpenRouterClient(api_key=api_key, transport=transport),
        policy=OpenRouterModelPolicy(),
    )
