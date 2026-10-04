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

from ..errors import (
    ArchitecturalIntelligenceConfigurationError,
    ArchitecturalIntelligenceProviderError,
)
from ..models import ArchitecturalDesignIntent
from .base import ArchitecturalReasoningInput

_SYSTEM = """You are the architectural reasoning layer for an Indian residential
planning system. Convert confirmed requirements into STRUCTURED SOFT DESIGN
INTENT for a deterministic solver.

Focus on functional zoning, entrance sequence, room relationships, privacy,
daylight, ventilation, service clustering, circulation, parking access, and
avoiding unusable leftover spaces. Precedents are topology evidence only: do
not copy coordinates, exact dimensions, geometry, or unsupported semantics.

CRITICAL AUTHORITY BOUNDARY:
- Do not draw or modify authoritative geometry.
- Do not output coordinates, walls, doors, polygons, or a finished plan.
- Do not invent exact dimensions. Preferred dimensions are allowed only when
  explicitly stated in confirmed requirements or confirmed room notes.
- Do not create hard constraints from architectural judgement.
- Architectural maximum areas remain preferences, never feasibility caps.
- Wet-stack coordination remains soft.
- Do not apply Vastu placement rules here.
- Safety, deterministic geometry, validators, and confirmed requirements win.
- Return one JSON object only, without markdown or prose.
"""


class NvidiaNimArchitecturalIntelligenceProvider:
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
    def from_environment(cls) -> NvidiaNimArchitecturalIntelligenceProvider:
        try:
            return cls(
                client=NvidiaNimClient.from_environment(),
                policy=NvidiaNimModelPolicy.from_environment(),
            )
        except NvidiaNimConfigurationError as exc:
            raise ArchitecturalIntelligenceConfigurationError(
                "NVIDIA NIM architectural provider is not configured."
            ) from exc

    def reason(
        self,
        request: ArchitecturalReasoningInput,
    ) -> ArchitecturalDesignIntent:
        confirmed_json = json.dumps(
            request.confirmed.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        precedent_text = ""
        if request.precedent_context:
            precedent_text = (
                "\n\nRetrieved residential precedent studies:\n"
                + json.dumps(
                    request.precedent_context,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n\nUse these only as advisory topology evidence."
            )
        user_text = (
            "Original client brief:\n"
            + request.original_prompt
            + "\n\nHuman-confirmed planning requirements:\n"
            + confirmed_json
            + precedent_text
            + "\n\n"
            + schema_instruction(ArchitecturalDesignIntent.model_json_schema())
        )

        def validate(parsed: dict[str, Any], model: str) -> ArchitecturalDesignIntent:
            payload = dict(parsed)
            payload.update(
                {
                    "schema_version": "26A.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": model,
                    "content_hash": None,
                }
            )
            return ArchitecturalDesignIntent.model_validate_json(
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
                temperature=0.2,
                response_format={"type": "json_object"},
            )
        except ProviderRuntimeError as exc:
            raise ArchitecturalIntelligenceProviderError(exc.category) from exc


def build_nvidia_nim_architectural_intelligence_for_test(
    *,
    api_key: str,
    transport: httpx.BaseTransport,
) -> NvidiaNimArchitecturalIntelligenceProvider:
    return NvidiaNimArchitecturalIntelligenceProvider(
        client=NvidiaNimClient(api_key=api_key, transport=transport),
        policy=NvidiaNimModelPolicy(),
    )
