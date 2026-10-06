from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ai_vastu.ollama_local_http import (
    OllamaLocalClient,
    OllamaLocalConfigurationError,
)
from ai_vastu.provider_runtime import ProviderRuntimeError

from .errors import ArchitecturalBrainConfigurationError, ArchitecturalBrainProviderError
from .models import ArchitecturalConcept, RetrievedPrecedent
from .provider import _brain_prompt


class _ArchitecturalConceptBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[ArchitecturalConcept]


def _program_output_schema(
    room_types: tuple[str, ...],
    concept_count: int,
) -> dict[str, Any]:
    """Constrain advisory references before generation to the compiled program."""
    schema = deepcopy(_ArchitecturalConceptBatch.model_json_schema())
    allowed = sorted(set(room_types))
    if not allowed:
        raise ValueError("Architectural Brain requires a nonempty room program.")
    definitions = schema["$defs"]
    definitions["ConceptRoom"]["properties"]["room_type"] = {
        "type": "string",
        "enum": allowed,
    }
    for field in ("source_room_type", "target_room_type"):
        definitions["TopologyEdge"]["properties"][field] = {
            "type": "string",
            "enum": allowed,
        }
    concept = definitions["ArchitecturalConcept"]
    # Identity, provenance and authority are supplied by application code.
    for field in (
        "schema_version",
        "project_id",
        "precedent_ids",
        "authoritative_geometry",
        "content_hash",
    ):
        concept["properties"].pop(field)
    concept["required"] = [field for field in concept["required"] if field in concept["properties"]]
    schema["properties"]["concepts"].update({"minItems": 1, "maxItems": concept_count})
    return schema


class OllamaLocalArchitecturalBrainProvider:
    """Local advisory topology provider; deterministic geometry stays authoritative."""

    def __init__(self, *, client: OllamaLocalClient) -> None:
        self._client = client

    @classmethod
    def from_environment(cls) -> OllamaLocalArchitecturalBrainProvider:
        try:
            return cls(client=OllamaLocalClient.from_environment())
        except OllamaLocalConfigurationError as exc:
            raise ArchitecturalBrainConfigurationError(
                "Local Ollama is not configured for the Architectural Brain."
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
            "Return an object with key 'concepts'. Every concept is advisory topology "
            "only; never emit CAD coordinates or authoritative geometry. "
            "Every rooms[].room_type and topology source_room_type/target_room_type "
            "must exactly match a room type in confirmed_program.room_types. "
            "Do not invent dining, corridor, or other rooms absent from that program. "
            "Return only concept_id, title, rooms, topology, and design_rationale "
            "for each concept. The application supplies identity and authority metadata."
        )
        schema = _program_output_schema(room_types, concept_count)
        allowed_room_types = frozenset(room_types)

        def validate(
            parsed: dict[str, Any],
            _model: str,
        ) -> tuple[ArchitecturalConcept, ...]:
            if set(parsed) != {"concepts"}:
                raise ValueError("Architectural Brain returned invalid wire fields.")
            raw_concepts = parsed.get("concepts")
            if not isinstance(raw_concepts, list) or not 1 <= len(raw_concepts) <= concept_count:
                raise ValueError("Architectural Brain returned no concepts.")
            concepts: list[ArchitecturalConcept] = []
            for raw in raw_concepts:
                if not isinstance(raw, dict):
                    raise ValueError("Architectural Brain concept was not an object.")
                item = dict(raw)
                item.update(
                    {
                        "schema_version": "26.4B.1",
                        "project_id": str(project_id),
                        "precedent_ids": [
                            precedent.fingerprint.precedent_id for precedent in precedents[:8]
                        ],
                        "authoritative_geometry": False,
                        "content_hash": None,
                    }
                )
                concept = ArchitecturalConcept.model_validate_json(json.dumps(item))
                # Fail closed even if a server ignores the decoding schema. No
                # aliases, dropping unknown edges, or post-generation correction.
                if any(room.room_type not in allowed_room_types for room in concept.rooms):
                    raise ValueError("Architectural Brain referenced an unavailable room type.")
                if any(
                    edge.source_room_type not in allowed_room_types
                    or edge.target_room_type not in allowed_room_types
                    for edge in concept.topology
                ):
                    raise ValueError(
                        "Architectural Brain referenced an unavailable topology endpoint."
                    )
                concepts.append(concept.with_content_hash())
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
                            "coordinates or authoritative geometry. Return strict JSON only."
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
                schema=schema,
                validator=validate,
            )
        except ProviderRuntimeError as exc:
            raise ArchitecturalBrainProviderError(exc.category) from exc
