from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryResult,
    OpeningBuildRequest,
    StairBuildRequest,
    WallBuildConfig,
)
from ai_vastu.constraints import CompiledConstraintProblem
from ai_vastu.plan_schema import (
    MM,
    Assumption,
    BuildableArea,
    IntPolygon,
    PositiveMM,
    RoomRequirement,
)
from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import EntityId
from ai_vastu.solver import PlannerConfig, PlannerResult, PlannerStatus
from ai_vastu.validation import DoorSwingContext, ValidationConfig, ValidationRunResult

GENERATION_PIPELINE_VERSION = "1.0.0"
NonNegativeInt = Annotated[int, Field(ge=0)]
_HASH_LENGTH = 64


class GenerationDisposition(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNSOLVED = "UNSOLVED"


class ArchitecturalGenerationRequest(FrozenModel):
    plot_boundary: IntPolygon
    buildable_area: BuildableArea
    room_requirements: tuple[RoomRequirement, ...]
    floor_id: EntityId
    floor_name: str
    floor_index: NonNegativeInt
    elevation_mm: MM
    floor_to_floor_mm: PositiveMM
    wall_config: WallBuildConfig
    planner_config: PlannerConfig
    validation_config: ValidationConfig
    assumptions: tuple[Assumption, ...] = ()
    openings: tuple[OpeningBuildRequest, ...] = ()
    stairs: tuple[StairBuildRequest, ...] = ()
    swing_contexts: tuple[DoorSwingContext, ...] = ()

    @model_validator(mode="after")
    def validate_generation_request(self) -> ArchitecturalGenerationRequest:
        if not self.floor_name.strip():
            raise ValueError("floor_name must not be blank.")
        if not self.room_requirements:
            raise ValueError("At least one room requirement is required for generation.")
        return self


class ArchitecturalGenerationResult(FrozenModel):
    pipeline_version: Literal["1.0.0"] = "1.0.0"
    disposition: GenerationDisposition
    problem: CompiledConstraintProblem
    planner_result: PlannerResult
    geometry_result: ArchitecturalGeometryResult | None = None
    validation_result: ValidationRunResult | None = None
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_result_shape(self) -> ArchitecturalGenerationResult:
        feasible = self.planner_result.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE)
        if feasible:
            if self.geometry_result is None or self.validation_result is None:
                raise ValueError(
                    "Feasible generation requires geometry and validation results."
                )
            expected = (
                GenerationDisposition.ACCEPTED
                if self.validation_result.report.valid
                else GenerationDisposition.REJECTED
            )
            if self.disposition is not expected:
                raise ValueError("Generation disposition does not match validation state.")
        else:
            if self.geometry_result is not None or self.validation_result is not None:
                raise ValueError("Unsolved generation cannot contain geometry or validation.")
            if self.disposition is not GenerationDisposition.UNSOLVED:
                raise ValueError("Non-feasible planner result must have UNSOLVED disposition.")

        if self.content_hash is not None:
            if len(self.content_hash) != _HASH_LENGTH or any(
                char not in "0123456789abcdef" for char in self.content_hash
            ):
                raise ValueError("content_hash must be a lowercase SHA-256 hex digest.")
            if self.content_hash != self.compute_content_hash():
                raise ValueError("content_hash does not match generation result content.")
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

    def with_content_hash(self) -> ArchitecturalGenerationResult:
        return self.model_copy(update={"content_hash": self.compute_content_hash()})
