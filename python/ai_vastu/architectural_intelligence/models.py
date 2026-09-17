from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ARCHITECTURAL_INTENT_VERSION = "26A.1"

Priority100 = Annotated[int, Field(ge=0, le=100)]
PositiveMM = Annotated[int, Field(gt=0)]
NonNegativeMM = Annotated[int, Field(ge=0)]
PositiveMM2 = Annotated[int, Field(gt=0)]


class SpaceZone(StrEnum):
    PUBLIC = "PUBLIC"
    SEMI_PRIVATE = "SEMI_PRIVATE"
    PRIVATE = "PRIVATE"
    SERVICE = "SERVICE"
    OUTDOOR = "OUTDOOR"


class RelationshipKind(StrEnum):
    ADJACENT = "ADJACENT"
    NEAR = "NEAR"
    SEPARATE = "SEPARATE"
    DIRECT_ACCESS = "DIRECT_ACCESS"


class FeatureKind(StrEnum):
    WARDROBE_WALL = "WARDROBE_WALL"
    FURNITURE_CLEARANCE = "FURNITURE_CLEARANCE"
    DAYLIGHT = "DAYLIGHT"
    CROSS_VENTILATION = "CROSS_VENTILATION"
    PLUMBING_CLUSTER = "PLUMBING_CLUSTER"
    ENTRY_PRIVACY = "ENTRY_PRIVACY"
    WORK_SURFACE = "WORK_SURFACE"
    STORAGE = "STORAGE"


class RoomFeatureIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: FeatureKind
    quantity: int = Field(default=1, ge=1, le=20)
    preferred_depth_mm: PositiveMM | None = None
    preferred_wall_length_mm: PositiveMM | None = None
    rationale: str = Field(min_length=1, max_length=500)


class RoomArchitecturalIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    room_type: str = Field(min_length=1, max_length=80)
    zone: SpaceZone
    privacy_priority: Priority100 = 50
    daylight_priority: Priority100 = 50
    ventilation_priority: Priority100 = 50
    user_priority: Priority100 = 50
    preferred_width_mm: PositiveMM | None = None
    preferred_depth_mm: PositiveMM | None = None
    preferred_area_mm2: PositiveMM2 | None = None
    features: tuple[RoomFeatureIntent, ...] = ()
    rationale: str = Field(min_length=1, max_length=1000)


class RelationshipIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_room_type: str = Field(min_length=1, max_length=80)
    target_room_type: str = Field(min_length=1, max_length=80)
    kind: RelationshipKind
    weight: Annotated[int, Field(ge=1, le=100)] = 70
    max_gap_mm: NonNegativeMM | None = None
    min_shared_length_mm: NonNegativeMM | None = None
    rationale: str = Field(min_length=1, max_length=500)


class CirculationIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    preferred_entry_room_types: tuple[str, ...] = ()
    avoid_direct_view_to_room_types: tuple[str, ...] = ()
    minimize_dead_end_corridors: bool = True
    minimize_internal_travel: bool = True
    notes: tuple[str, ...] = ()


class ArchitecturalDesignIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["26A.1"] = "26A.1"
    project_id: UUID
    draft_id: UUID
    provider: str = Field(min_length=1, max_length=80)
    model: str | None = Field(default=None, max_length=200)

    strategy_summary: str = Field(min_length=1, max_length=2000)
    room_intents: tuple[RoomArchitecturalIntent, ...] = ()
    relationships: tuple[RelationshipIntent, ...] = ()
    circulation: CirculationIntent = CirculationIntent()
    planning_notes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_intent(self) -> ArchitecturalDesignIntent:
        room_keys = [item.room_type.strip().lower() for item in self.room_intents]
        if len(room_keys) != len(set(room_keys)):
            raise ValueError("room_intents must contain at most one entry per room type.")

        relationship_keys = [
            (
                item.source_room_type.strip().lower(),
                item.target_room_type.strip().lower(),
                item.kind.value,
            )
            for item in self.relationships
        ]
        if len(relationship_keys) != len(set(relationship_keys)):
            raise ValueError("Duplicate architectural relationships are not allowed.")

        if self.content_hash is not None:
            if len(self.content_hash) != 64 or any(
                char not in "0123456789abcdef" for char in self.content_hash
            ):
                raise ValueError("content_hash must be a lowercase SHA-256 hex digest.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match architectural intent content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return text.encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> ArchitecturalDesignIntent:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
