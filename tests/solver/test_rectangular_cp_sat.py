from __future__ import annotations

from itertools import combinations

from ai_vastu.solver import PlannerStatus, solve_rectangular_problem

from .helpers import compiled_problem, config


def _overlap_area(a: object, b: object) -> int:
    left = max(a.x_mm, b.x_mm)  # type: ignore[attr-defined]
    right = min(a.x_mm + a.width_mm, b.x_mm + b.width_mm)  # type: ignore[attr-defined]
    bottom = max(a.y_mm, b.y_mm)  # type: ignore[attr-defined]
    top = min(a.y_mm + a.depth_mm, b.y_mm + b.depth_mm)  # type: ignore[attr-defined]
    return max(0, right - left) * max(0, top - bottom)


def test_solver_places_rectangles_inside_buildable_area_without_overlap() -> None:
    result = solve_rectangular_problem(compiled_problem(), config=config())
    assert result.status is PlannerStatus.OPTIMAL
    assert len(result.placements) == 3
    for placement in result.placements:
        assert placement.x_mm >= 0
        assert placement.y_mm >= 0
        assert placement.x_mm + placement.width_mm <= 10_000
        assert placement.y_mm + placement.depth_mm <= 8_000
        assert placement.width_mm % 100 == 0
        assert placement.depth_mm % 100 == 0
        assert placement.area_mm2 == placement.width_mm * placement.depth_mm
    for first, second in combinations(result.placements, 2):
        assert _overlap_area(first, second) == 0


def test_same_problem_and_config_produce_same_hashed_result() -> None:
    problem = compiled_problem()
    planner_config = config()
    first = solve_rectangular_problem(problem, config=planner_config)
    second = solve_rectangular_problem(problem, config=planner_config)
    assert first.status is PlannerStatus.OPTIMAL
    assert first.content_hash == second.content_hash
    assert first.placements == second.placements
    assert first.objective_contributions == second.objective_contributions


def test_problem_hash_is_recorded_even_when_compiler_hash_field_is_empty() -> None:
    problem = compiled_problem()
    assert problem.content_hash is not None
    result = solve_rectangular_problem(problem, config=config())
    assert result.metadata.problem_hash == problem.content_hash


def test_soft_objectives_not_yet_modeled_are_reported_not_silently_dropped() -> None:
    result = solve_rectangular_problem(compiled_problem(), config=config())
    codes = {notice.code for notice in result.notices}
    assert "SOFT_OBJECTIVE_NOT_YET_OPTIMIZED" in codes
