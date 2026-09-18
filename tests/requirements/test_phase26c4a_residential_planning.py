from __future__ import annotations

from uuid import UUID

from ai_vastu.constraints import ConstraintCompilerInput, compile_constraints
from ai_vastu.requirements.generation_adapter import compile_confirmed_requirements
from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    ConfirmedRoomRequirement,
    Direction,
)
from ai_vastu.requirements.residential_planning import local_boundary_side
from ai_vastu.solver import (
    PlannerBoundarySide,
    PlannerStatus,
    solve_rectangular_problem,
)


def _confirmed(*, bedroom_count: int = 2) -> ConfirmedRequirements:
    return ConfirmedRequirements(
        draft_id=UUID("30000000-0000-0000-0000-000000000001"),
        user_id=UUID("30000000-0000-0000-0000-000000000002"),
        project_id=UUID("30000000-0000-0000-0000-000000000003"),
        user_confirmed=True,
        plot_width_mm=10_000,
        plot_depth_mm=10_000,
        north_rotation_deg=0,
        road_side=Direction.E,
        entrance_facing=Direction.E,
        floor_count=1,
        bedroom_count=bedroom_count,
        parking_count=1,
        rooms=[
            ConfirmedRoomRequirement(room_type="living", quantity=1, floor_preference=0),
            ConfirmedRoomRequirement(room_type="kitchen", quantity=1, floor_preference=0),
            ConfirmedRoomRequirement(
                room_type="bedroom",
                quantity=bedroom_count,
                floor_preference=0,
            ),
            ConfirmedRoomRequirement(
                room_type="common_toilet",
                quantity=1,
                floor_preference=0,
            ),
        ],
    )


def test_true_direction_maps_to_local_rectangular_boundary() -> None:
    assert local_boundary_side("E", north_rotation_deg=0) is PlannerBoundarySide.EAST
    assert local_boundary_side("E", north_rotation_deg=90) is PlannerBoundarySide.SOUTH


def test_compile_adds_residential_topology_and_boundary_context() -> None:
    compiled = compile_confirmed_requirements(_confirmed())
    planning = compiled.request.planner_config.residential_planning

    assert planning.enabled is True
    assert planning.target_occupied_area_basis_points == 7_000
    assert planning.road_boundary_side is PlannerBoundarySide.EAST
    assert planning.entrance_boundary_side is PlannerBoundarySide.EAST
    assert planning.require_road_connected_parking is True
    assert planning.require_entrance_boundary_access is True

    room_types = [item.room_type.value for item in compiled.request.room_requirements]
    assert "lobby" in room_types

    assert any(
        assumption.code == "PHASE26C4A_RESIDENTIAL_PLANNING"
        for assumption in compiled.request.assumptions
    )


def test_solver_anchors_parking_and_entry_and_uses_auto_area_target() -> None:
    confirmed = _confirmed(bedroom_count=1)
    compiled = compile_confirmed_requirements(confirmed)
    request = compiled.request
    planner_config = request.planner_config.model_copy(
        update={
            "solver_step_mm": 50,
            "max_time_ms": 5_000,
            "max_conflicts": 200_000,
        }
    )
    problem = compile_constraints(
        ConstraintCompilerInput(
            buildable_area=request.buildable_area,
            available_floor_indices=(request.floor_index,),
            room_requirements=request.room_requirements,
            assumptions=request.assumptions,
        )
    )

    result = solve_rectangular_problem(problem, config=planner_config)

    assert result.status in {PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE}
    by_type: dict[str, list[object]] = {}
    for placement in result.placements:
        by_type.setdefault(placement.room_type.value, []).append(placement)

    parking = by_type["parking"][0]
    living = by_type["living"][0]
    assert parking.x_mm + parking.width_mm == 10_000
    assert living.x_mm + living.width_mm == 10_000

    occupied_area = sum(item.area_mm2 for item in result.placements)
    utilization_bp = occupied_area * 10_000 // 100_000_000
    assert utilization_bp >= 6_000

    contribution_kinds = {item.kind for item in result.objective_contributions}
    assert "RESIDENTIAL_OCCUPIED_AREA_TARGET" in contribution_kinds
    assert "RESIDENTIAL_ROOM_AREA_BALANCE" in contribution_kinds
    assert "RESIDENTIAL_COMPACTNESS_VOID" in contribution_kinds
    assert "RESIDENTIAL_TOPOLOGY_ADJACENCY" in contribution_kinds
