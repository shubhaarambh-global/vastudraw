from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

from .models import ArchitecturalConcept, RetrievedPrecedent
from .precedent_store import JsonlPrecedentStore, PrecedentQuery
from .provider import create_architectural_brain_provider


@dataclass(frozen=True, slots=True)
class ArchitecturalBrainRun:
    precedents: tuple[RetrievedPrecedent, ...]
    concepts: tuple[ArchitecturalConcept, ...]


class ArchitecturalBrainService:
    def __init__(self, store: JsonlPrecedentStore) -> None:
        self._store = store

    @classmethod
    def from_environment(cls) -> ArchitecturalBrainService:
        path = os.getenv(
            "AI_VASTU_PRECEDENT_INDEX_PATH",
            ".local/architectural-precedents.jsonl",
        )
        production = os.getenv("APP_ENV", "development").strip().lower() == "production"
        return cls(JsonlPrecedentStore(path, production_mode=production))

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
        concept_count: int = 6,
    ) -> ArchitecturalBrainRun:
        precedents = self._store.retrieve(
            PrecedentQuery(
                width_mm=width_mm,
                depth_mm=depth_mm,
                bedroom_count=bedroom_count,
                toilet_count=toilet_count,
                parking_count=parking_count,
                room_types=frozenset(room_types),
                road_side=road_side,
                entrance_side=entrance_side,
            ),
            limit=24,
        )
        concepts = create_architectural_brain_provider().propose(
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
        return ArchitecturalBrainRun(precedents=precedents, concepts=concepts)
