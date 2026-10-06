from __future__ import annotations

from ai_vastu.solver import (
    CirculationRepairPair,
    PlannerStatus,
    ResidentialPlanningConfig,
    RoomPlacement,
    solve_rectangular_problem,
)

from .helpers import (
    bedroom_requirement,
    compiled_problem,
    config,
    dining_requirement,
    living_requirement,
)


def _shared_wall_length_mm(first: RoomPlacement, second: RoomPlacement) -> int:
    first_x = first.x_mm
    first_y = first.y_mm
    first_w = first.width_mm
    first_d = first.depth_mm
    second_x = second.x_mm
    second_y = second.y_mm
    second_w = second.width_mm
    second_d = second.depth_mm

    first_right = first_x + first_w
    second_right = second_x + second_w
    first_top = first_y + first_d
    second_top = second_y + second_d

    if first_right == second_x or second_right == first_x:
        return max(0, min(first_top, second_top) - max(first_y, second_y))
    if first_top == second_y or second_top == first_y:
        return max(0, min(first_right, second_right) - max(first_x, second_x))
    return 0


def test_system_derived_circulation_repair_enforces_door_capable_adjacency() -> None:
    living = living_requirement().model_copy(update={"adjacency_preferences": ()})
    bedroom = bedroom_requirement().model_copy(update={"adjacency_preferences": ()})
    problem = compiled_problem(requirements=(living, bedroom))
    room_ids = {room.room_type.value: room.id for room in problem.room_instances}

    repair = CirculationRepairPair(
        first_room_id=room_ids["living"],
        second_room_id=room_ids["bedroom"],
        min_shared_length_mm=1_000,
    )
    planner_config = config().model_copy(
        update={
            "residential_planning": ResidentialPlanningConfig(
                enabled=True,
                target_occupied_area_basis_points=7_000,
                circulation_repair_pairs=(repair,),
            )
        }
    )

    result = solve_rectangular_problem(problem, config=planner_config)

    assert result.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE)
    placements = {item.room_type.value: item for item in result.placements}
    assert _shared_wall_length_mm(placements["living"], placements["bedroom"]) >= 1_000
    assert "CIRCULATION_REPAIR_ENFORCED" in {notice.code for notice in result.notices}


def test_hard_circulation_keeps_dining_on_public_room_network() -> None:
    requirements = tuple(
        room.model_copy(update={"adjacency_preferences": ()})
        for room in (living_requirement(), dining_requirement(), bedroom_requirement())
    )
    problem = compiled_problem(requirements=requirements)
    planner_config = config().model_copy(
        update={
            "residential_planning": ResidentialPlanningConfig(
                enabled=True,
                require_horizontal_circulation=True,
                target_occupied_area_basis_points=7000,
            ),
        }
    )
    result = solve_rectangular_problem(problem, config=planner_config)
    assert result.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE)
    placements = {item.room_type.value: item for item in result.placements}
    assert _shared_wall_length_mm(placements["living"], placements["dining"]) >= 1000
    assert (
        max(
            _shared_wall_length_mm(placements[public], placements["bedroom"])
            for public in ("living", "dining")
        )
        >= 1000
    )
