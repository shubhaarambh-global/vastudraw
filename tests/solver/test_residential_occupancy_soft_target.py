from __future__ import annotations

from ai_vastu.solver import PlannerStatus, solve_rectangular_problem
from ai_vastu.solver.models import ResidentialPlanningConfig

from .helpers import compiled_problem, config, living_requirement


def test_high_occupancy_target_remains_soft_when_confirmed_room_bounds_are_smaller() -> None:
    requirement = living_requirement().model_copy(
        update={
            "preferred_width_mm": 3_300,
            "max_width_mm": 3_500,
            "preferred_depth_mm": 3_300,
            "max_depth_mm": 3_500,
            "preferred_area_mm2": 11_000_000,
            "adjacency_preferences": (),
        }
    )

    problem = compiled_problem(
        requirements=(requirement,),
    )

    planner_config = config().model_copy(
        update={
            "residential_planning": ResidentialPlanningConfig(
                enabled=True,
                target_occupied_area_basis_points=9_000,
                occupied_area_weight=40,
                room_area_balance_weight=10,
                compactness_weight=40,
            )
        }
    )

    result = solve_rectangular_problem(
        problem,
        config=planner_config,
    )

    assert result.status is PlannerStatus.OPTIMAL
    assert len(result.placements) == 1

    placement = result.placements[0]

    # The 90% residential occupancy target is deliberately impossible here:
    # the confirmed room bounds permit at most 3.5 m x 3.5 m = 12.25 m2.
    # A planning preference must not override those authoritative bounds or
    # turn the otherwise feasible problem into an infeasible one.
    assert placement.width_mm <= 3_500
    assert placement.depth_mm <= 3_500
    assert placement.area_mm2 <= 12_250_000

    notice_codes = {notice.code for notice in result.notices}

    assert "RESIDENTIAL_OCCUPANCY_FLOOR_ENFORCED" not in notice_codes
    assert "RESIDENTIAL_PLANNING_TARGET_ACTIVE" in notice_codes
