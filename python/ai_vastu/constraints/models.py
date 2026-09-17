from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import (
    Assumption,
    BuildableArea,
    EntityId,
    RoomRequirement,
    RoomType,
)
from ai_vastu.plan_schema.units import NonNegativeMM, PositiveMM, PositiveMM2, Priority100

CONSTRAINT_PROBLEM_VERSION = "1.0.0"
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
_HASH_RE_LENGTH = 64


class DimensionAxis(StrEnum):
    WIDTH = "WIDTH"
    DEPTH = "DEPTH"


class ConstraintOrigin(StrEnum):
    ARCHITECTURAL_INVARIANT = "ARCHITECTURAL_INVARIANT"
    USER_REQUIREMENT = "USER_REQUIREMENT"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class HardConstraintKind(StrEnum):
    CONTAINMENT = "CONTAINMENT"
    MIN_DIMENSION = "MIN_DIMENSION"
    MAX_DIMENSION = "MAX_DIMENSION"
    MIN_AREA = "MIN_AREA"
    MAX_AREA = "MAX_AREA"
    ASPECT_RATIO = "ASPECT_RATIO"
    AVAILABLE_FLOORS = "AVAILABLE_FLOORS"
    ADJACENCY_PROHIBITION = "ADJACENCY_PROHIBITION"


class SoftConstraintKind(StrEnum):
    PREFERRED_DIMENSION = "PREFERRED_DIMENSION"
    PREFERRED_AREA = "PREFERRED_AREA"
    FLOOR_PREFERENCE = "FLOOR_PREFERENCE"
    ADJACENCY_PREFERENCE = "ADJACENCY_PREFERENCE"
    ADJACENCY_AVOIDANCE = "ADJACENCY_AVOIDANCE"
    ROOM_PRIORITIES = "ROOM_PRIORITIES"


class ConstraintNoticeSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class RoomInstance(FrozenModel):
    id: EntityId
    requirement_id: EntityId
    ordinal: PositiveInt
    room_type: RoomType
    locked: bool
    vastu_profile_refs: tuple[str, ...] = ()


class ContainmentConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.CONTAINMENT] = HardConstraintKind.CONTAINMENT
    origin: Literal[ConstraintOrigin.ARCHITECTURAL_INVARIANT] = (
        ConstraintOrigin.ARCHITECTURAL_INVARIANT
    )
    room_instance_id: EntityId


class MinimumDimensionConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.MIN_DIMENSION] = HardConstraintKind.MIN_DIMENSION
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    axis: DimensionAxis
    minimum_mm: PositiveMM


class MaximumDimensionConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.MAX_DIMENSION] = HardConstraintKind.MAX_DIMENSION
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    axis: DimensionAxis
    maximum_mm: PositiveMM


class MinimumAreaConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.MIN_AREA] = HardConstraintKind.MIN_AREA
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    minimum_area_mm2: PositiveMM2


class MaximumAreaConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.MAX_AREA] = HardConstraintKind.MAX_AREA
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    maximum_area_mm2: PositiveMM2


class AspectRatioConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.ASPECT_RATIO] = HardConstraintKind.ASPECT_RATIO
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    min_ratio_milli: PositiveInt
    max_ratio_milli: PositiveInt


class AvailableFloorsConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.AVAILABLE_FLOORS] = HardConstraintKind.AVAILABLE_FLOORS
    origin: Literal[ConstraintOrigin.ARCHITECTURAL_INVARIANT] = (
        ConstraintOrigin.ARCHITECTURAL_INVARIANT
    )
    room_instance_id: EntityId
    allowed_floor_indices: tuple[NonNegativeInt, ...]

    @model_validator(mode="after")
    def validate_floors(self) -> AvailableFloorsConstraint:
        if not self.allowed_floor_indices:
            raise ValueError("At least one available floor is required.")
        if len(self.allowed_floor_indices) != len(set(self.allowed_floor_indices)):
            raise ValueError("allowed_floor_indices must be unique.")
        return self


class AdjacencyProhibitionConstraint(FrozenModel):
    id: EntityId
    kind: Literal[HardConstraintKind.ADJACENCY_PROHIBITION] = (
        HardConstraintKind.ADJACENCY_PROHIBITION
    )
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    target_room_type: RoomType


HardConstraint = Annotated[
    ContainmentConstraint
    | MinimumDimensionConstraint
    | MaximumDimensionConstraint
    | MinimumAreaConstraint
    | MaximumAreaConstraint
    | AspectRatioConstraint
    | AvailableFloorsConstraint
    | AdjacencyProhibitionConstraint,
    Field(discriminator="kind"),
]


class PreferredDimensionObjective(FrozenModel):
    id: EntityId
    kind: Literal[SoftConstraintKind.PREFERRED_DIMENSION] = SoftConstraintKind.PREFERRED_DIMENSION
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    axis: DimensionAxis
    preferred_mm: PositiveMM
    weight: Priority100


class PreferredAreaObjective(FrozenModel):
    id: EntityId
    kind: Literal[SoftConstraintKind.PREFERRED_AREA] = SoftConstraintKind.PREFERRED_AREA
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    preferred_area_mm2: PositiveMM2
    weight: Priority100


class FloorPreferenceObjective(FrozenModel):
    id: EntityId
    kind: Literal[SoftConstraintKind.FLOOR_PREFERENCE] = SoftConstraintKind.FLOOR_PREFERENCE
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    preferred_floor_indices: tuple[NonNegativeInt, ...]
    weight: Priority100


class AdjacencyPreferenceObjective(FrozenModel):
    id: EntityId
    kind: Literal[SoftConstraintKind.ADJACENCY_PREFERENCE] = SoftConstraintKind.ADJACENCY_PREFERENCE
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    target_room_type: RoomType
    weight: Priority100
    max_gap_mm: NonNegativeMM | None = None
    min_shared_length_mm: NonNegativeMM | None = None


class AdjacencyAvoidanceObjective(FrozenModel):
    id: EntityId
    kind: Literal[SoftConstraintKind.ADJACENCY_AVOIDANCE] = SoftConstraintKind.ADJACENCY_AVOIDANCE
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    target_room_type: RoomType
    weight: Priority100 | None = None
    weight_source: Literal["UNSPECIFIED_IN_REQUIREMENT"] = "UNSPECIFIED_IN_REQUIREMENT"


class RoomPrioritiesObjective(FrozenModel):
    id: EntityId
    kind: Literal[SoftConstraintKind.ROOM_PRIORITIES] = SoftConstraintKind.ROOM_PRIORITIES
    origin: Literal[ConstraintOrigin.USER_REQUIREMENT] = ConstraintOrigin.USER_REQUIREMENT
    room_instance_id: EntityId
    privacy_priority: Priority100
    daylight_priority: Priority100
    ventilation_priority: Priority100
    user_priority: Priority100


SoftConstraint = Annotated[
    PreferredDimensionObjective
    | PreferredAreaObjective
    | FloorPreferenceObjective
    | AdjacencyPreferenceObjective
    | AdjacencyAvoidanceObjective
    | RoomPrioritiesObjective,
    Field(discriminator="kind"),
]


class CompilerNotice(FrozenModel):
    code: str
    severity: ConstraintNoticeSeverity
    requirement_id: EntityId | None = None
    message: str


class ConstraintCompilerInput(FrozenModel):
    buildable_area: BuildableArea
    available_floor_indices: tuple[NonNegativeInt, ...]
    room_requirements: tuple[RoomRequirement, ...]
    assumptions: tuple[Assumption, ...] = ()

    @model_validator(mode="after")
    def validate_identity_sets(self) -> ConstraintCompilerInput:
        if not self.available_floor_indices:
            raise ValueError("At least one available floor is required.")
        if len(self.available_floor_indices) != len(set(self.available_floor_indices)):
            raise ValueError("available_floor_indices must be unique.")
        requirement_ids = [item.id for item in self.room_requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("RoomRequirement IDs must be unique.")
        assumption_ids = [item.id for item in self.assumptions]
        if len(assumption_ids) != len(set(assumption_ids)):
            raise ValueError("Assumption IDs must be unique.")
        return self


class CompiledConstraintProblem(FrozenModel):
    problem_version: Literal["1.0.0"] = "1.0.0"
    buildable_area: BuildableArea
    available_floor_indices: tuple[NonNegativeInt, ...]
    room_instances: tuple[RoomInstance, ...]
    hard_constraints: tuple[HardConstraint, ...]
    soft_constraints: tuple[SoftConstraint, ...]
    assumptions: tuple[Assumption, ...] = ()
    notices: tuple[CompilerNotice, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_hash(self) -> CompiledConstraintProblem:
        if self.content_hash is None:
            return self
        if len(self.content_hash) != _HASH_RE_LENGTH or any(
            char not in "0123456789abcdef" for char in self.content_hash
        ):
            raise ValueError("content_hash must be a lowercase SHA-256 hex digest.")
        if self.content_hash != self.compute_content_hash():
            raise ValueError("content_hash does not match canonical constraint problem content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return text.encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> CompiledConstraintProblem:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
