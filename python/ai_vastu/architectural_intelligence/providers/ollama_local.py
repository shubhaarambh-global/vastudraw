from __future__ import annotations

import json
from typing import Any

from ai_vastu.ollama_local_http import (
    OllamaLocalClient,
    OllamaLocalConfigurationError,
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

CRITICAL AUTHORITY BOUNDARY:
- Do not draw or modify authoritative geometry.
- Do not output coordinates, walls, doors, polygons, or a finished plan.
- Do not invent exact dimensions.
- Do not create hard constraints from architectural judgement.
- Architectural maximum areas remain preferences, never feasibility caps.
- Wet-stack coordination remains soft.
- Do not apply Vastu placement rules here.
- Safety, deterministic geometry, validators, and confirmed requirements win.
- Return one strict JSON object only.
"""


class OllamaLocalArchitecturalIntelligenceProvider:
    name = "ollama_local"

    def __init__(self, *, client: OllamaLocalClient) -> None:
        self._client = client

    @classmethod
    def from_environment(cls) -> OllamaLocalArchitecturalIntelligenceProvider:
        try:
            return cls(client=OllamaLocalClient.from_environment())
        except OllamaLocalConfigurationError as exc:
            raise ArchitecturalIntelligenceConfigurationError(
                "Local Ollama architectural provider is not configured."
            ) from exc

    def reason(self, request: ArchitecturalReasoningInput) -> ArchitecturalDesignIntent:
        user_payload: dict[str, Any] = {
            "original_client_brief": request.original_prompt,
            "confirmed_requirements": request.confirmed.model_dump(mode="json"),
            "precedent_context": request.precedent_context,
            "authority": "advisory topology and design intent only",
        }

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
                    {
                        "role": "user",
                        "content": json.dumps(
                            user_payload,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    },
                ),
                schema=ArchitecturalDesignIntent.model_json_schema(),
                validator=validate,
            )
        except ProviderRuntimeError as exc:
            raise ArchitecturalIntelligenceProviderError(exc.category) from exc
