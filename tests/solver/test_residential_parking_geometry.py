import pytest
from ortools.sat.python import cp_model

from ai_vastu.solver.models import (
    PlannerBoundarySide,
    ResidentialPlanningConfig,
)
from ai_vastu.solver.rectangular_cp_sat import (
    _apply_parking_clear_dimension_constraints,
    _RoomVars,
)


@pytest.mark.parametrize(
    ("side", "expected_width_mm", "expected_depth_mm"),
    (
        (PlannerBoundarySide.NORTH, 3_000, 5_500),
        (PlannerBoundarySide.SOUTH, 3_000, 5_500),
        (PlannerBoundarySide.EAST, 5_500, 3_000),
        (PlannerBoundarySide.WEST, 5_500, 3_000),
    ),
)
def test_parking_clear_bay_dimensions_follow_road_orientation(
    side: PlannerBoundarySide,
    expected_width_mm: int,
    expected_depth_mm: int,
) -> None:
    model = cp_model.CpModel()

    clear_width_mm = model.new_int_var(
        1,
        10_000,
        "clear_width_mm",
    )
    clear_depth_mm = model.new_int_var(
        1,
        10_000,
        "clear_depth_mm",
    )

    room = _RoomVars(
        x=None,
        y=None,
        width=None,
        depth=None,
        x_end=None,
        y_end=None,
        area_cells2=None,
        clear_width_mm=clear_width_mm,
        clear_depth_mm=clear_depth_mm,
        clear_area_mm2=None,
        x_interval=None,
        y_interval=None,
    )

    planning = ResidentialPlanningConfig(
        enabled=True,
        road_boundary_side=side,
        require_road_connected_parking=True,
        parking_min_frontage_mm=3_000,
        parking_min_depth_mm=5_500,
    )

    _apply_parking_clear_dimension_constraints(
        model,
        room,
        side=side,
        planning=planning,
    )

    model.minimize(clear_width_mm + clear_depth_mm)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in {
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    }
    assert solver.value(clear_width_mm) == expected_width_mm
    assert solver.value(clear_depth_mm) == expected_depth_mm


def test_parking_dimension_config_defaults_are_residential_usable() -> None:
    planning = ResidentialPlanningConfig()

    assert planning.parking_min_frontage_mm == 3_000
    assert planning.parking_min_depth_mm == 5_500
