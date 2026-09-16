from uuid import UUID

import pytest

from ai_vastu.orientation import (
    AmbiguousRoadFacingError,
    Direction8,
    analyze_road_facing,
    classify_direction8,
    create_orientation,
    drawing_bearing_udeg,
    edge_direction_analysis,
    orientation_from_drawing_north,
    require_uniform_road_facing_direction,
)
from ai_vastu.plan_schema import (
    IntPoint,
    LengthUnit,
    OrientationSource,
    Plot,
    PlotInputSource,
    VerificationStatus,
)
from ai_vastu.plot import create_polygon_plot, create_rectangular_plot, create_road

PLOT_ID = UUID("40000000-0000-0000-0000-000000000001")
ROAD_ID = UUID("40000000-0000-0000-0000-000000000010")


def _rectangle() -> Plot:
    return create_rectangular_plot(
        plot_id=PLOT_ID,
        width_value=10_000,
        width_unit=LengthUnit.MM,
        depth_value=15_000,
        depth_unit=LengthUnit.MM,
    )


def test_exact_north_rotation_is_fixed_point_microdegrees() -> None:
    orientation = create_orientation(
        north_rotation_degrees="13.72",
        source=OrientationSource.USER,
        verified=True,
    )

    assert orientation.north_rotation_udeg == 13_720_000
    assert orientation.verified is True


def test_simple_ui_north_direction_maps_to_exact_rotation() -> None:
    orientation = orientation_from_drawing_north(Direction8.NE)
    assert orientation.north_rotation_udeg == 45_000_000


def test_direction8_sector_boundaries_are_deterministic() -> None:
    assert classify_direction8(22_499_999) is Direction8.N
    assert classify_direction8(22_500_000) is Direction8.NE
    assert classify_direction8(337_500_000) is Direction8.N


def test_drawing_bearing_uses_plus_y_as_zero_and_clockwise_positive() -> None:
    origin = IntPoint(x_mm=0, y_mm=0)
    assert drawing_bearing_udeg(origin, IntPoint(x_mm=0, y_mm=1)) == 0
    assert drawing_bearing_udeg(origin, IntPoint(x_mm=1, y_mm=0)) == 90_000_000
    assert drawing_bearing_udeg(origin, IntPoint(x_mm=1, y_mm=1)) == 45_000_000


def test_rectangle_edge_facing_uses_outward_normal_not_tangent() -> None:
    plot = _rectangle()
    orientation = create_orientation(north_rotation_degrees=0)

    bottom = edge_direction_analysis(plot, plot.edge_ids[0], orientation)
    right = edge_direction_analysis(plot, plot.edge_ids[1], orientation)
    top = edge_direction_analysis(plot, plot.edge_ids[2], orientation)
    left = edge_direction_analysis(plot, plot.edge_ids[3], orientation)

    assert bottom.outward_direction_8 is Direction8.S
    assert right.outward_direction_8 is Direction8.E
    assert top.outward_direction_8 is Direction8.N
    assert left.outward_direction_8 is Direction8.W


def test_road_direction_changes_with_true_north_without_changing_plot_geometry() -> None:
    plot = _rectangle()
    orientation = create_orientation(north_rotation_degrees=90)
    analysis = edge_direction_analysis(plot, plot.edge_ids[1], orientation)

    assert analysis.outward_drawing_bearing_udeg == 90_000_000
    assert analysis.outward_true_bearing_udeg == 0
    assert analysis.outward_direction_8 is Direction8.N


def test_clockwise_polygon_gets_correct_outward_normal() -> None:
    plot = create_polygon_plot(
        plot_id=PLOT_ID,
        vertices=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=0, y_mm=10_000),
            IntPoint(x_mm=10_000, y_mm=10_000),
            IntPoint(x_mm=10_000, y_mm=0),
        ),
        input_source=PlotInputSource.SURVEY,
        verification_status=VerificationStatus.SURVEY_VERIFIED,
    )
    orientation = create_orientation(north_rotation_degrees=0)

    left_edge = edge_direction_analysis(plot, plot.edge_ids[0], orientation)
    assert left_edge.outward_direction_8 is Direction8.W


def test_compound_road_does_not_invent_one_facing_when_edges_disagree() -> None:
    plot = _rectangle()
    road = create_road(
        plot=plot,
        road_id=ROAD_ID,
        plot_edge_ids=(plot.edge_ids[1], plot.edge_ids[2]),
    )
    orientation = create_orientation(north_rotation_degrees=0)

    analysis = analyze_road_facing(plot, road, orientation)
    assert analysis.uniform_direction_8 is None
    with pytest.raises(AmbiguousRoadFacingError):
        require_uniform_road_facing_direction(plot, road, orientation)
