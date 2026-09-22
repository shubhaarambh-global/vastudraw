from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.geometry import IntPoint, IntPolygon
from ai_vastu.plan_schema.models import EntityId, RoomType
from ai_vastu.plan_schema.units import MM, NonNegativeMM, PositiveMM

SOLVER_MODEL_VERSION = "1.0.0"
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
SeedInt = Annotated[int, Field(ge=0, le=2_147_483_647)]
BasisPointsInt = Annotated[int, Field(ge=0, le=10_000)]
_HASH_LENGTH = 64


class PlannerStatus(StrEnum):
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"


class PlannerNoticeSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class PlannerSearchVariant(StrEnum):
    LOWER_LEFT = "LOWER_LEFT"
    LOWER_RIGHT = "LOWER_RIGHT"
    UPPER_LEFT = "UPPER_LEFT"
    UPPER_RIGHT = "UPPER_RIGHT"
    REVERSE_LOWER_LEFT = "REVERSE_LOWER_LEFT"
    REVERSE_UPPER_RIGHT = "REVERSE_UPPER_RIGHT"


class PlannerBoundarySide(StrEnum):
    SOUTH = "SOUTH"
    EAST = "EAST"
    NORTH = "NORTH"
    WEST = "WEST"


class CirculationRepairPair(FrozenModel):
    first_room_id: EntityId
    second_room_id: EntityId
    min_shared_length_mm: PositiveMM

    @model_validator(mode="after")
    def validate_distinct_rooms(self) -> CirculationRepairPair:
        if self.first_room_id == self.second_room_id:
            raise ValueError("Circulation repair must connect two distinct rooms.")
        return self


class ResidentialPlanningConfig(FrozenModel):
    enabled: bool = False
    target_occupied_area_basis_points: BasisPointsInt = 7_000
    occupied_area_weight: NonNegativeInt = 40
    room_area_balance_weight: NonNegativeInt = 10
    compactness_weight: NonNegativeInt = 40
    road_boundary_side: PlannerBoundarySide | None = None
    entrance_boundary_side: PlannerBoundarySide | None = None
    require_road_connected_parking: bool = False
    parking_min_frontage_mm: PositiveMM = 3_000
    parking_min_depth_mm: PositiveMM = 5_500
    require_entrance_boundary_access: bool = False
    require_horizontal_circulation: bool = False
    circulation_repair_pairs: tuple[CirculationRepairPair, ...] = ()
    vertical_core_footprint: IntPolygon | None = None
    wet_stack_anchor: IntPoint | None = None
    wet_stack_targets: tuple[tuple[RoomType, IntPoint], ...] = ()
    wet_stack_weight: NonNegativeInt = 100


class PlannerConfig(FrozenModel):
    solver_step_mm: PositiveMM
    clearance_reserve_mm: NonNegativeMM = 0
    search_variant: PlannerSearchVariant = PlannerSearchVariant.LOWER_LEFT
    residential_planning: ResidentialPlanningConfig = ResidentialPlanningConfig()
    max_time_ms: PositiveInt
    max_conflicts: PositiveInt
    random_seed: SeedInt = 0
    num_search_workers: Literal[1] = 1


class PlannerNotice(FrozenModel):
    code: str
    severity: PlannerNoticeSeverity
    message: str
    constraint_id: EntityId | None = None
    room_instance_id: EntityId | None = None


class ObjectiveContribution(FrozenModel):
    constraint_id: EntityId
    kind: str
    penalty_units: NonNegativeInt
    weight: NonNegativeInt
    weighted_penalty: NonNegativeInt


class RoomPlacement(FrozenModel):
    room_instance_id: EntityId
    room_type: RoomType
    floor_index: NonNegativeInt
    x_mm: MM
    y_mm: MM
    width_mm: PositiveMM
    depth_mm: PositiveMM
    area_mm2: PositiveInt


class SolverRunMetadata(FrozenModel):
    solver_name: Literal["OR_TOOLS_CP_SAT"] = "OR_TOOLS_CP_SAT"
    solver_version: str
    model_version: Literal["1.0.0"] = "1.0.0"
    problem_hash: str
    config: PlannerConfig

    @model_validator(mode="after")
    def validate_hash(self) -> SolverRunMetadata:
        if len(self.problem_hash) != _HASH_LENGTH or any(
            char not in "0123456789abcdef" for char in self.problem_hash
        ):
            raise ValueError("problem_hash must be lowercase SHA-256 hex.")
        return self


class PlannerResult(FrozenModel):
    status: PlannerStatus
    metadata: SolverRunMetadata
    placements: tuple[RoomPlacement, ...] = ()
    objective_penalty: NonNegativeInt | None = None
    objective_contributions: tuple[ObjectiveContribution, ...] = ()
    notices: tuple[PlannerNotice, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> PlannerResult:
        if self.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
            if not self.placements:
                raise ValueError("Feasible planner results require placements.")
            if self.objective_penalty is None:
                raise ValueError("Feasible planner results require objective_penalty.")
        elif self.placements:
            raise ValueError("Non-feasible planner results cannot contain placements.")

        if self.content_hash is not None:
            if len(self.content_hash) != _HASH_LENGTH or any(
                char not in "0123456789abcdef" for char in self.content_hash
            ):
                raise ValueError("content_hash must be lowercase SHA-256 hex.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match planner result content.")
        return self

    def canonical_content_bytes(self) -> bytes:
        payload = self.model_dump(mode="json", exclude={"content_hash"})
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self.canonical_content_bytes()).hexdigest()

    def with_content_hash(self) -> PlannerResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
