from __future__ import annotations

from uuid import UUID

import pytest

from ai_vastu.constraints import (
    AdjacencyProhibitionConstraint,
    ConstraintOrigin,
    HardConstraintKind,
)
from ai_vastu.plan_schema import BuildableArea, IntPoint, IntPolygon, RoomRequirement, RoomType
from ai_vastu.solver import (
    PlannerStatus,
    UnsupportedSolverProblemError,
    solve_rectangular_problem,
)

from .helpers import compiled_problem, config, dining_requirement, living_requirement


def test_rejects_multi_floor_problem_in_phase7() -> None:
    problem = compiled_problem().model_copy(update={"available_floor_indices": (0, 1)})
    with pytest.raises(UnsupportedSolverProblemError, match="exactly one available floor"):
        solve_rectangular_problem(problem, config=config())


def test_rejects_irregular_buildable_area() -> None:
    polygon = IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=10_000, y_mm=0),
            IntPoint(x_mm=9_000, y_mm=8_000),
            IntPoint(x_mm=0, y_mm=8_000),
        )
    )
    problem = compiled_problem().model_copy(
        update={"buildable_area": BuildableArea(polygon=polygon)}
    )
    with pytest.raises(UnsupportedSolverProblemError, match="axis-aligned rectangular"):
        solve_rectangular_problem(problem, config=config())


def test_rejects_locked_room_without_existing_geometry() -> None:
    locked = living_requirement().model_copy(update={"locked": True})
    problem = compiled_problem(requirements=(locked, dining_requirement()))
    with pytest.raises(UnsupportedSolverProblemError, match="Locked rooms"):
        solve_rectangular_problem(problem, config=config())


def test_hard_adjacency_prohibition_fails_closed_until_modeled() -> None:
    problem = compiled_problem(requirements=(living_requirement(), dining_requirement()))
    room_id = problem.room_instances[0].id
    constraint = AdjacencyProhibitionConstraint(
        id=UUID("72000000-0000-0000-0000-000000000099"),
        kind=HardConstraintKind.ADJACENCY_PROHIBITION,
        origin=ConstraintOrigin.USER_REQUIREMENT,
        room_instance_id=room_id,
        target_room_type=RoomType.DINING,
    )
    problem = problem.model_copy(
        update={"hard_constraints": (*problem.hard_constraints, constraint)}
    )
    with pytest.raises(
        UnsupportedSolverProblemError,
        match="Hard adjacency prohibitions",
    ):
        solve_rectangular_problem(problem, config=config())


def test_lattice_infeasibility_returns_explicit_infeasible_result() -> None:
    tiny = RoomRequirement(
        id=UUID("72000000-0000-0000-0000-000000000010"),
        room_type=RoomType.STORE,
        min_width_mm=3_050,
        max_width_mm=3_050,
        min_depth_mm=3_050,
        max_depth_mm=3_050,
        min_area_mm2=9_000_000,
    )
    problem = compiled_problem(
        width_mm=4_000,
        depth_mm=4_000,
        requirements=(tiny,),
    )
    result = solve_rectangular_problem(problem, config=config(step_mm=100))
    assert result.status is PlannerStatus.INFEASIBLE
    assert result.placements == ()
    assert {notice.code for notice in result.notices} == {"SOLVER_LATTICE_INFEASIBLE"}
