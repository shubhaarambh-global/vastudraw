from uuid import UUID

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryRequest,
    WallBuildConfig,
    build_architectural_geometry,
)
from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.plan_schema import BuildableArea, IntPoint, IntPolygon, RoomRequirement, RoomType
from ai_vastu.solver import PlannerConfig, PlannerStatus, solve_rectangular_problem


def rectangle(width_mm: int, depth_mm: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=0),
            IntPoint(x_mm=width_mm, y_mm=depth_mm),
            IntPoint(x_mm=0, y_mm=depth_mm),
        )
    )


requirements = (
    RoomRequirement(
        id=UUID("83000000-0000-0000-0000-000000000001"),
        room_type=RoomType.LIVING,
        min_width_mm=3000,
        preferred_width_mm=3600,
        max_width_mm=4500,
        min_depth_mm=3000,
        preferred_depth_mm=3600,
        max_depth_mm=4500,
        min_area_mm2=10_000_000,
        user_priority=80,
    ),
    RoomRequirement(
        id=UUID("83000000-0000-0000-0000-000000000002"),
        room_type=RoomType.DINING,
        min_width_mm=2700,
        preferred_width_mm=3000,
        max_width_mm=4000,
        min_depth_mm=2700,
        preferred_depth_mm=3000,
        max_depth_mm=4000,
        min_area_mm2=8_000_000,
        user_priority=70,
    ),
)
problem = compile_constraints(
    ConstraintCompilerInput(
        buildable_area=BuildableArea(polygon=rectangle(9000, 7000)),
        available_floor_indices=(0,),
        room_requirements=requirements,
    )
)
planner = solve_rectangular_problem(
    problem,
    config=PlannerConfig(
        solver_step_mm=100,
        max_time_ms=5000,
        max_conflicts=100000,
        random_seed=19,
    ),
)
if planner.status not in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
    raise SystemExit(f"Geometry smoke requires a feasible planner result, got {planner.status}.")
request = ArchitecturalGeometryRequest(
    problem=problem,
    planner_result=planner,
    floor_id=UUID("83000000-0000-0000-0000-000000000010"),
    floor_name="Ground Floor",
    elevation_mm=0,
    floor_to_floor_mm=3300,
    wall_config=WallBuildConfig(
        external_wall_thickness_mm=230,
        internal_wall_thickness_mm=115,
        wall_height_mm=3000,
    ),
)
first = build_architectural_geometry(request)
second = build_architectural_geometry(request)
if first.content_hash != second.content_hash or first.floor != second.floor:
    raise SystemExit("Architectural geometry is not deterministic.")
print(
    "Architectural geometry deterministic: "
    f"rooms={len(first.floor.rooms)}, walls={len(first.floor.walls)}, "
    f"hash={first.content_hash}"
)
