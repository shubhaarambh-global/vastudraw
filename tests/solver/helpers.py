from __future__ import annotations

from uuid import UUID

from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.plan_schema import (
    AdjacencyPreference,
    BuildableArea,
    IntPoint,
    IntPolygon,
    RoomRequirement,
    RoomType,
)
from ai_vastu.solver import PlannerConfig


def rectangle(width_mm: int = 10_000, depth_mm: int = 8_000) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=depth_mm),
            IntPoint(x_mm=0, y_mm=depth_mm),
        )
    )


def living_requirement() -> RoomRequirement:
    return RoomRequirement(
        id=UUID("72000000-0000-0000-0000-000000000001"),
        room_type=RoomType.LIVING,
        min_width_mm=3_000,
        preferred_width_mm=3_600,
        max_width_mm=5_000,
        min_depth_mm=3_000,
        preferred_depth_mm=4_000,
        max_depth_mm=5_000,
        min_area_mm2=10_000_000,
        preferred_area_mm2=14_000_000,
        adjacency_preferences=(
            AdjacencyPreference(
                target_room_type=RoomType.DINING,
                weight=80,
                max_gap_mm=200,
                min_shared_length_mm=1_200,
            ),
        ),
        user_priority=80,
    )


def dining_requirement() -> RoomRequirement:
    return RoomRequirement(
        id=UUID("72000000-0000-0000-0000-000000000002"),
        room_type=RoomType.DINING,
        min_width_mm=2_700,
        preferred_width_mm=3_300,
        max_width_mm=4_500,
        min_depth_mm=2_700,
        preferred_depth_mm=3_300,
        max_depth_mm=4_500,
        min_area_mm2=8_000_000,
        preferred_area_mm2=10_000_000,
        user_priority=70,
    )


def bedroom_requirement() -> RoomRequirement:
    return RoomRequirement(
        id=UUID("72000000-0000-0000-0000-000000000003"),
        room_type=RoomType.BEDROOM,
        min_width_mm=3_000,
        preferred_width_mm=3_300,
        max_width_mm=4_500,
        min_depth_mm=3_000,
        preferred_depth_mm=3_600,
        max_depth_mm=4_500,
        min_area_mm2=9_000_000,
        preferred_area_mm2=11_000_000,
        user_priority=75,
    )


def compiled_problem(
    *,
    width_mm: int = 10_000,
    depth_mm: int = 8_000,
    requirements: tuple[RoomRequirement, ...] | None = None,
):
    return compile_constraints(
        ConstraintCompilerInput(
            buildable_area=BuildableArea(polygon=rectangle(width_mm, depth_mm)),
            available_floor_indices=(0,),
            room_requirements=(
                requirements
                if requirements is not None
                else (living_requirement(), dining_requirement(), bedroom_requirement())
            ),
        )
    )


def config(*, step_mm: int = 100) -> PlannerConfig:
    return PlannerConfig(
        solver_step_mm=step_mm,
        max_time_ms=10_000,
        max_conflicts=200_000,
        random_seed=11,
    )
