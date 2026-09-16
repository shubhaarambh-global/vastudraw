from uuid import UUID

from ai_vastu.plan_schema import IntPoint, LengthUnit, VerificationStatus
from ai_vastu.plot import create_rectangular_plot, derive_edge_ids, plot_edges

PLOT_ID = UUID("10000000-0000-0000-0000-000000000001")


def test_30_by_50_foot_plot_is_exact_integer_mm() -> None:
    plot = create_rectangular_plot(
        plot_id=PLOT_ID,
        width_value=30,
        width_unit=LengthUnit.FT,
        depth_value=50,
        depth_unit=LengthUnit.FT,
        verification_status=VerificationStatus.USER_VERIFIED,
    )

    assert plot.boundary.outer == (
        IntPoint(x_mm=0, y_mm=0),
        IntPoint(x_mm=9_144, y_mm=0),
        IntPoint(x_mm=9_144, y_mm=15_240),
        IntPoint(x_mm=0, y_mm=15_240),
    )
    assert plot.declared_measurements[0].exact_mm_decimal == "9144"
    assert plot.declared_measurements[1].exact_mm_decimal == "15240"
    assert plot.declared_measurements[0].rounding_delta_mm_decimal == "0"
    assert plot.edge_ids == derive_edge_ids(PLOT_ID, 4)


def test_10_by_18_metre_plot_is_exact_integer_mm() -> None:
    plot = create_rectangular_plot(
        plot_id=PLOT_ID,
        width_value=10,
        width_unit=LengthUnit.M,
        depth_value=18,
        depth_unit=LengthUnit.M,
    )

    assert plot.boundary.outer[1].x_mm == 10_000
    assert plot.boundary.outer[2].y_mm == 18_000


def test_rectangle_origin_is_explicit_local_datum() -> None:
    plot = create_rectangular_plot(
        plot_id=PLOT_ID,
        width_value=4_000,
        width_unit=LengthUnit.MM,
        depth_value=6_000,
        depth_unit=LengthUnit.MM,
        origin=IntPoint(x_mm=-500, y_mm=1_200),
    )

    assert plot.boundary.outer == (
        IntPoint(x_mm=-500, y_mm=1_200),
        IntPoint(x_mm=3_500, y_mm=1_200),
        IntPoint(x_mm=3_500, y_mm=7_200),
        IntPoint(x_mm=-500, y_mm=7_200),
    )


def test_edge_order_is_stable_and_follows_boundary_order() -> None:
    plot = create_rectangular_plot(
        plot_id=PLOT_ID,
        width_value=4_000,
        width_unit=LengthUnit.MM,
        depth_value=6_000,
        depth_unit=LengthUnit.MM,
    )
    edges = plot_edges(plot)

    assert [edge.index for edge in edges] == [0, 1, 2, 3]
    assert edges[0].start == plot.boundary.outer[0]
    assert edges[0].end == plot.boundary.outer[1]
    assert edges[3].end == plot.boundary.outer[0]
