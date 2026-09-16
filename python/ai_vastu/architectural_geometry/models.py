from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.constraints.models import CompiledConstraintProblem
from ai_vastu.plan_schema import (
    MM,
    DoorHinge,
    DoorSwing,
    Floor,
    MicroDegrees,
    NonNegativeMM,
    OpeningKind,
    PositiveMM,
    StairType,
)
from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import EntityId
from ai_vastu.solver.models import PlannerResult

ARCHITECTURAL_GEOMETRY_VERSION = "1.0.0"
PositiveInt = Annotated[int, Field(gt=0)]
_HASH_LENGTH = 64


class GeometryNoticeSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"


class WallBuildConfig(FrozenModel):
    external_wall_thickness_mm: PositiveMM
    internal_wall_thickness_mm: PositiveMM
    wall_height_mm: PositiveMM
    external_construction_type: str | None = None
    internal_construction_type: str | None = None


class OpeningBuildRequest(FrozenModel):
    wall_id: EntityId
    kind: OpeningKind
    offset_from_wall_start_mm: NonNegativeMM
    width_mm: PositiveMM
    height_mm: PositiveMM
    sill_height_mm: NonNegativeMM | None = None
    hinge: DoorHinge | None = None
    swing: DoorSwing | None = None


class StairBuildRequest(FrozenModel):
    room_instance_id: EntityId
    stair_type: StairType
    width_mm: PositiveMM
    riser_mm: PositiveMM
    tread_mm: PositiveMM
    number_of_risers: PositiveInt
    floor_height_mm: PositiveMM
    landing_depth_mm: NonNegativeMM
    direction_udeg: MicroDegrees
    headroom_mm: PositiveMM | None = None


class ArchitecturalGeometryRequest(FrozenModel):
    problem: CompiledConstraintProblem
    planner_result: PlannerResult
    floor_id: EntityId
    floor_name: str
    elevation_mm: MM
    floor_to_floor_mm: PositiveMM
    wall_config: WallBuildConfig
    openings: tuple[OpeningBuildRequest, ...] = ()
    stairs: tuple[StairBuildRequest, ...] = ()


class GeometryNotice(FrozenModel):
    code: str
    severity: GeometryNoticeSeverity
    message: str
    entity_id: EntityId | None = None


class ArchitecturalGeometryResult(FrozenModel):
    geometry_version: Literal["1.0.0"] = "1.0.0"
    source_problem_hash: str
    source_planner_hash: str
    floor: Floor
    notices: tuple[GeometryNotice, ...] = ()
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_hashes(self) -> ArchitecturalGeometryResult:
        for name, value in (
            ("source_problem_hash", self.source_problem_hash),
            ("source_planner_hash", self.source_planner_hash),
        ):
            if len(value) != _HASH_LENGTH or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} must be lowercase SHA-256 hex.")
        if self.content_hash is not None:
            if len(self.content_hash) != _HASH_LENGTH or any(
                c not in "0123456789abcdef" for c in self.content_hash
            ):
                raise ValueError("content_hash must be lowercase SHA-256 hex.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match architectural geometry content.")
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

    def with_content_hash(self) -> ArchitecturalGeometryResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
