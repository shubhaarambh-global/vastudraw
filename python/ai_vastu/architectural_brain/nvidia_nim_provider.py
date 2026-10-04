from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from ai_vastu.nvidia_nim_http import (
    NvidiaNimClient,
    NvidiaNimConfigurationError,
    NvidiaNimModelPolicy,
    schema_instruction,
)
from ai_vastu.provider_runtime import ProviderRuntimeError

from .errors import ArchitecturalBrainConfigurationError, ArchitecturalBrainProviderError
from .models import ArchitecturalConcept, RetrievedPrecedent
from .provider import _brain_prompt


class NvidiaNimArchitecturalBrainProvider:
    """NVIDIA-backed advisory topology provider; never authoritative geometry."""

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
    def from_environment(cls) -> NvidiaNimArchitecturalBrainProvider:
        try:
            return cls(
                client=NvidiaNimClient.from_environment(),
                policy=NvidiaNimModelPolicy.from_environment(),
            )
        except NvidiaNimConfigurationError as exc:
            raise ArchitecturalBrainConfigurationError(
                "NVIDIA NIM is not configured for the Architectural Brain."
            ) from exc

    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        width_mm: int,
        depth_mm: int,
        bedroom_count: int,
        toilet_count: int,
        parking_count: int,
        room_types: tuple[str, ...],
        road_side: str | None,
        entrance_side: str | None,
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]:
        prompt = _brain_prompt(
            project_id=project_id,
            original_prompt=original_prompt,
            width_mm=width_mm,
            depth_mm=depth_mm,
            bedroom_count=bedroom_count,
            toilet_count=toilet_count,
            parking_count=parking_count,
            room_types=room_types,
            road_side=road_side,
            entrance_side=entrance_side,
            precedents=precedents,
            concept_count=concept_count,
        )
        prompt["output_contract"] = (
            "Return an object with key 'concepts'. Each item is advisory topology "
            "only and must validate as ArchitecturalConcept. "
            + schema_instruction(ArchitecturalConcept.model_json_schema())
        )

        def validate(
            parsed: dict[str, Any],
            _model: str,
        ) -> tuple[ArchitecturalConcept, ...]:
            raw_concepts = parsed.get("concepts")
            if not isinstance(raw_concepts, list) or not raw_concepts:
                raise ValueError("Architectural Brain returned no concepts.")
            concepts: list[ArchitecturalConcept] = []
            for raw in raw_concepts[:concept_count]:
                if not isinstance(raw, dict):
                    raise ValueError("Architectural Brain concept was not an object.")
                item = dict(raw)
                item.update(
                    {
                        "schema_version": "26.4B.1",
                        "project_id": str(project_id),
                        "precedent_ids": [
                            precedent.fingerprint.precedent_id
                            for precedent in precedents[:8]
                        ],
                        "authoritative_geometry": False,
                        "content_hash": None,
                    }
                )
                concepts.append(
                    ArchitecturalConcept.model_validate_json(
                        json.dumps(item)
                    ).with_content_hash()
                )
            if not concepts:
                raise ValueError("Architectural Brain returned no valid concepts.")
            return tuple(concepts)

        try:
            return self._client.complete_validated_json(
                messages=(
                    {
                        "role": "system",
                        "content": (
                            "Produce advisory Indian residential topology, zoning, access, "
                            "room proportion, and site-use intent only. Never emit CAD "
                            "coordinates or authoritative geometry. Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            prompt,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    },
                ),
                models=self._policy.text_chain,
                validator=validate,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except ProviderRuntimeError as exc:
            raise ArchitecturalBrainProviderError(exc.category) from exc
