from __future__ import annotations

from uuid import UUID

from ai_vastu.architectural_geometry import ArchitecturalGeometryRequest, WallBuildConfig
from ai_vastu.solver import solve_rectangular_problem
from tests.solver.helpers import compiled_problem, config


def build_request() -> ArchitecturalGeometryRequest:
    problem = compiled_problem()
    planner = solve_rectangular_problem(problem, config=config())
    return ArchitecturalGeometryRequest(
        problem=problem,
        planner_result=planner,
        floor_id=UUID("81000000-0000-0000-0000-000000000001"),
        floor_name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3300,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3000,
        ),
    )


def t_junction_request() -> ArchitecturalGeometryRequest:
    from ai_vastu.constraints.models import CompiledConstraintProblem, RoomInstance
    from ai_vastu.plan_schema import BuildableArea, IntPoint, IntPolygon, RoomType
    from ai_vastu.solver.models import (
        PlannerConfig,
        PlannerResult,
        PlannerStatus,
        RoomPlacement,
        SolverRunMetadata,
    )

    boundary = IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=6000, y_mm=0),
            IntPoint(x_mm=6000, y_mm=4000),
            IntPoint(x_mm=0, y_mm=4000),
        )
    )
    room_specs = (
        (
            UUID("84000000-0000-0000-0000-000000000001"),
            UUID("84000000-0000-0000-0000-000000000011"),
            RoomType.LIVING,
            0,
            0,
            3000,
            4000,
        ),
        (
            UUID("84000000-0000-0000-0000-000000000002"),
            UUID("84000000-0000-0000-0000-000000000012"),
            RoomType.DINING,
            3000,
            0,
            3000,
            2000,
        ),
        (
            UUID("84000000-0000-0000-0000-000000000003"),
            UUID("84000000-0000-0000-0000-000000000013"),
            RoomType.BEDROOM,
            3000,
            2000,
            3000,
            2000,
        ),
    )
    rooms = tuple(
        RoomInstance(
            id=room_id,
            requirement_id=requirement_id,
            ordinal=1,
            room_type=room_type,
            locked=False,
        )
        for room_id, requirement_id, room_type, *_ in room_specs
    )
    problem = CompiledConstraintProblem(
        buildable_area=BuildableArea(polygon=boundary),
        available_floor_indices=(0,),
        room_instances=rooms,
        hard_constraints=(),
        soft_constraints=(),
    ).with_content_hash()
    placements = tuple(
        RoomPlacement(
            room_instance_id=room_id,
            room_type=room_type,
            floor_index=0,
            x_mm=x,
            y_mm=y,
            width_mm=width,
            depth_mm=depth,
            area_mm2=width * depth,
        )
        for room_id, _requirement_id, room_type, x, y, width, depth in room_specs
    )
    planner = PlannerResult(
        status=PlannerStatus.OPTIMAL,
        metadata=SolverRunMetadata(
            solver_version="phase8-test-fixture",
            problem_hash=problem.content_hash,
            config=PlannerConfig(
                solver_step_mm=100,
                max_time_ms=1000,
                max_conflicts=1000,
            ),
        ),
        placements=placements,
        objective_penalty=0,
    ).with_content_hash()
    return ArchitecturalGeometryRequest(
        problem=problem,
        planner_result=planner,
        floor_id=UUID("84000000-0000-0000-0000-000000000020"),
        floor_name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3300,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3000,
        ),
    )
