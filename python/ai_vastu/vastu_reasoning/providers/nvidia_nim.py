from __future__ import annotations

import json
from typing import Any

import httpx

from ai_vastu.nvidia_nim_http import (
    NvidiaNimClient,
    NvidiaNimConfigurationError,
    NvidiaNimModelPolicy,
    schema_instruction,
)
from ai_vastu.provider_runtime import ProviderRuntimeError

from ..errors import VastuReasoningConfigurationError, VastuReasoningProviderError
from ..models import VastuReasoningProfile
from .base import VastuReasoningInput

_SYSTEM = """You are the Vastu reasoning layer for an Indian residential
planning system. Reason only over the application-supplied source-backed catalog.

CRITICAL POLICY:
- Vastu remains a SOFT design influence only.
- Never invent rules or turn a principle into a hard geometry constraint.
- Never override safety, statutory requirements, confirmed must-haves, usable
  dimensions, circulation, accessibility, structure, or deterministic geometry.
- Do not change catalog sectors or invent rule IDs.
- Return one entry for every catalog rule.
- Preserve non-adjustable defaults and source disagreement.
- Return one JSON object only, without markdown or prose.
"""


class NvidiaNimVastuReasoningProvider:
    name = "nvidia_nim"

    def __init__(
        self,
        *,
        client: NvidiaNimClient,
        policy: NvidiaNimModelPolicy,
    ) -> None:
        policy.validate()
        self._client = client
        self._policy = policy

    @classmethod
    def from_environment(cls) -> NvidiaNimVastuReasoningProvider:
        try:
            return cls(
                client=NvidiaNimClient.from_environment(),
                policy=NvidiaNimModelPolicy.from_environment(),
            )
        except NvidiaNimConfigurationError as exc:
            raise VastuReasoningConfigurationError(
                "NVIDIA NIM Vastu reasoning provider is not configured."
            ) from exc

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
                    # Service normalization applies the confirmed influence mode.
                    "influence_mode": "balanced",
                    "architecture_weight_basis_points": 5000,
                    "vastu_weight_basis_points": 5000,
                    "content_hash": None,
                }
            )
            return VastuReasoningProfile.model_validate_json(
                json.dumps(payload)
            ).with_content_hash()

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_text},
                ),
                models=self._policy.text_chain,
                validator=validate,
                temperature=0.15,
                response_format={"type": "json_object"},
            )
        except ProviderRuntimeError as exc:
            raise VastuReasoningProviderError(exc.category) from exc


def build_nvidia_nim_vastu_provider_for_test(
    *,
    api_key: str,
    transport: httpx.BaseTransport,
) -> NvidiaNimVastuReasoningProvider:
    return NvidiaNimVastuReasoningProvider(
        client=NvidiaNimClient(api_key=api_key, transport=transport),
        policy=NvidiaNimModelPolicy(),
    )
