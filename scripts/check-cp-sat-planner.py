from __future__ import annotations

from uuid import UUID

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
        id=UUID("71000000-0000-0000-0000-000000000001"),
        room_type=RoomType.LIVING,
        min_width_mm=3000,
        preferred_width_mm=3600,
        max_width_mm=5000,
        min_depth_mm=3000,
        preferred_depth_mm=4000,
        max_depth_mm=5000,
        min_area_mm2=10_000_000,
        user_priority=80,
    ),
    RoomRequirement(
        id=UUID("71000000-0000-0000-0000-000000000002"),
        room_type=RoomType.BEDROOM,
        min_width_mm=3000,
        preferred_width_mm=3300,
        max_width_mm=4500,
        min_depth_mm=3000,
        preferred_depth_mm=3600,
        max_depth_mm=4500,
        min_area_mm2=9_000_000,
        user_priority=70,
    ),
)
problem = compile_constraints(
    ConstraintCompilerInput(
        buildable_area=BuildableArea(polygon=rectangle(9000, 8000)),
        available_floor_indices=(0,),
        room_requirements=requirements,
    )
)
config = PlannerConfig(
    solver_step_mm=100,
    max_time_ms=5000,
    max_conflicts=100_000,
    random_seed=17,
)
first = solve_rectangular_problem(problem, config=config)
second = solve_rectangular_problem(problem, config=config)
if first.status is not PlannerStatus.OPTIMAL:
    raise SystemExit(f"Expected OPTIMAL smoke solution, got {first.status}.")
if first.content_hash != second.content_hash:
    raise SystemExit("Deterministic planner smoke run produced different result hashes.")
print(
    "CP-SAT planner deterministic: "
    f"status={first.status}, rooms={len(first.placements)}, "
    f"penalty={first.objective_penalty}, hash={first.content_hash}"
)
