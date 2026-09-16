from __future__ import annotations

from uuid import UUID

import pytest

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryRequest,
    StairBuildRequest,
    StairConstructionError,
    WallBuildConfig,
    build_architectural_geometry,
)
from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.plan_schema import BuildableArea, RoomRequirement, RoomType, StairType
from ai_vastu.solver import PlannerConfig, solve_rectangular_problem
from tests.solver.helpers import rectangle


def _stair_request(room_type: RoomType = RoomType.STAIRCASE) -> ArchitecturalGeometryRequest:
    requirement = RoomRequirement(
        id=UUID("82000000-0000-0000-0000-000000000001"),
        room_type=room_type,
        min_width_mm=2500,
        max_width_mm=3000,
        min_depth_mm=4000,
        max_depth_mm=4500,
        min_area_mm2=10_000_000,
    )
    problem = compile_constraints(
        ConstraintCompilerInput(
            buildable_area=BuildableArea(polygon=rectangle(6000, 6000)),
            available_floor_indices=(0,),
            room_requirements=(requirement,),
        )
    )
    planner = solve_rectangular_problem(
        problem,
        config=PlannerConfig(
            solver_step_mm=100,
            max_time_ms=5000,
            max_conflicts=100000,
            random_seed=7,
        ),
    )
    room_id = planner.placements[0].room_instance_id
    return ArchitecturalGeometryRequest(
        problem=problem,
        planner_result=planner,
        floor_id=UUID("82000000-0000-0000-0000-000000000002"),
        floor_name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3300,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3000,
        ),
        stairs=(
            StairBuildRequest(
                room_instance_id=room_id,
                stair_type=StairType.STRAIGHT,
                width_mm=1000,
                riser_mm=165,
                tread_mm=270,
                number_of_risers=20,
                floor_height_mm=3300,
                landing_depth_mm=1000,
                direction_udeg=0,
                headroom_mm=2100,
            ),
        ),
    )


def test_explicit_stair_uses_staircase_room_envelope() -> None:
    request = _stair_request()
    built = build_architectural_geometry(request)
    assert len(built.floor.stairs) == 1
    assert built.floor.stairs[0].footprint == built.floor.rooms[0].polygon


def test_stair_rejects_non_staircase_room() -> None:
    request = _stair_request(RoomType.STORE)
    with pytest.raises(StairConstructionError, match="staircase room"):
        build_architectural_geometry(request)
