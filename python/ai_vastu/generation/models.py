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
    VerticalCorePlan,
    WallBuildConfig,
    WholeBuildingValidation,
)
from ai_vastu.constraints import CompiledConstraintProblem
from ai_vastu.plan_schema import (
    MM,
    Assumption,
    BuildableArea,
    IntPolygon,
    NonNegativeMM,
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


class CirculationGenerationConfig(FrozenModel):
    auto_generate: bool = False
    internal_door_width_mm: PositiveMM = 800
    external_door_width_mm: PositiveMM = 900
    edge_margin_mm: NonNegativeMM = 100
    door_height_mm: PositiveMM = 2100
    require_external_entry: bool = True


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
    circulation_config: CirculationGenerationConfig = CirculationGenerationConfig()
    floor_count: PositiveMM = 1
    floor_requirements: tuple[tuple[RoomRequirement, ...], ...] = ()
    floor_buildable_areas: tuple[BuildableArea, ...] = ()
    vertical_circulation_status: Literal[
        "GROUND_ONLY",
        "RESERVED_FOR_2D9G",
        "PLANNING_REQUIRED",
        "PLANNED",
    ] = "GROUND_ONLY"
    vertical_core_plan: VerticalCorePlan | None = None

    @model_validator(mode="after")
    def validate_generation_request(self) -> ArchitecturalGenerationRequest:
        if not self.floor_name.strip():
            raise ValueError("floor_name must not be blank.")
        if not self.room_requirements:
            raise ValueError("At least one room requirement is required for generation.")
        if self.floor_count < 1 or self.floor_count > 4:
            raise ValueError("Supported residential generation is limited to 1-4 floors.")
        if self.floor_requirements and len(self.floor_requirements) != self.floor_count:
            raise ValueError("floor_requirements must contain one partition per floor.")
        if self.floor_buildable_areas and len(self.floor_buildable_areas) != self.floor_count:
            raise ValueError("floor_buildable_areas must contain one footprint per floor.")
        if self.floor_count > 1 and self.vertical_circulation_status not in {
            "RESERVED_FOR_2D9G",
            "PLANNING_REQUIRED",
            "PLANNED",
        }:
            raise ValueError("Multi-floor generation must plan vertical circulation.")
        if self.vertical_circulation_status == "PLANNED" and self.vertical_core_plan is None:
            raise ValueError("PLANNED vertical circulation requires a core plan.")
        return self


class FloorGenerationResult(FrozenModel):
    floor_index: NonNegativeInt
    problem: CompiledConstraintProblem
    planner_result: PlannerResult
    geometry_result: ArchitecturalGeometryResult | None = None
    validation_result: ValidationRunResult | None = None


class ArchitecturalGenerationResult(FrozenModel):
    pipeline_version: Literal["1.0.0"] = "1.0.0"
    disposition: GenerationDisposition
    problem: CompiledConstraintProblem
    planner_result: PlannerResult
    geometry_result: ArchitecturalGeometryResult | None = None
    validation_result: ValidationRunResult | None = None
    floor_results: tuple[FloorGenerationResult, ...] = ()
    vertical_circulation_status: Literal[
        "GROUND_ONLY",
        "RESERVED_FOR_2D9G",
        "PLANNED",
        "VALIDATED",
    ] = "GROUND_ONLY"
    vertical_core_plan: VerticalCorePlan | None = None
    building_validation: WholeBuildingValidation | None = None
    content_hash: str | None = None

    @model_validator(mode="after")
    def validate_result_shape(self) -> ArchitecturalGenerationResult:
        if self.floor_results:
            all_feasible = all(
                item.planner_result.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE)
                for item in self.floor_results
            )
            all_floor_valid = all(
                item.geometry_result is not None
                and item.validation_result is not None
                and item.validation_result.report.valid
                for item in self.floor_results
            )
            building_valid = (
                self.building_validation is not None and self.building_validation.accepted
            )
            expected = (
                GenerationDisposition.ACCEPTED
                if all_feasible and all_floor_valid and building_valid
                else GenerationDisposition.REJECTED
                if all_feasible
                else GenerationDisposition.UNSOLVED
            )
            if self.disposition is not expected:
                raise ValueError("Generation disposition does not match whole-building state.")
            if all_feasible and self.building_validation is None:
                raise ValueError(
                    "Solved multi-floor generation requires whole-building validation."
                )
            if self.vertical_core_plan is None:
                raise ValueError("Multi-floor generation requires a vertical-core plan.")
            if building_valid and self.vertical_circulation_status != "VALIDATED":
                raise ValueError("Accepted multi-floor generation must mark its core VALIDATED.")
            if self.content_hash is not None:
                if len(self.content_hash) != _HASH_LENGTH or any(
                    char not in "0123456789abcdef" for char in self.content_hash
                ):
                    raise ValueError("content_hash must be a lowercase SHA-256 hex digest.")
                if self.content_hash != self.compute_content_hash():
                    raise ValueError("content_hash does not match generation result content.")
            return self

        feasible = self.planner_result.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE)
        if feasible:
            if self.geometry_result is None or self.validation_result is None:
                raise ValueError("Feasible generation requires geometry and validation results.")
            floor_valid = self.validation_result.report.valid
            expected = (
                GenerationDisposition.ACCEPTED
                if floor_valid
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
