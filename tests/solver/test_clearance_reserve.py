from __future__ import annotations

from ai_vastu.solver import PlannerStatus, solve_rectangular_problem

from .helpers import bedroom_requirement, compiled_problem, config


def test_explicit_clearance_reserve_protects_clear_room_minima() -> None:
    bedroom = bedroom_requirement().model_copy(
        update={
            "preferred_width_mm": None,
            "preferred_depth_mm": None,
            "preferred_area_mm2": None,
            "max_width_mm": None,
            "max_depth_mm": None,
        }
    )
    problem = compiled_problem(
        width_mm=6_000,
        depth_mm=6_000,
        requirements=(bedroom,),
    )
    planner_config = config(step_mm=10).model_copy(update={"clearance_reserve_mm": 230})

    result = solve_rectangular_problem(problem, config=planner_config)

    assert result.status is PlannerStatus.OPTIMAL
    placement = result.placements[0]
    assert placement.width_mm >= bedroom.min_width_mm + 230
    assert placement.depth_mm >= bedroom.min_depth_mm + 230
    conservative_clear_width = placement.width_mm - 230
    conservative_clear_depth = placement.depth_mm - 230
    assert conservative_clear_width >= bedroom.min_width_mm
    assert conservative_clear_depth >= bedroom.min_depth_mm
    assert conservative_clear_width * conservative_clear_depth >= bedroom.min_area_mm2
