from uuid import UUID

import pytest

from ai_vastu.plan_schema import LengthUnit, Plot
from ai_vastu.plot import (
    InvalidRoadDefinitionError,
    UnknownPlotEdgeError,
    create_rectangular_plot,
    create_road,
    validate_road_set,
)

PLOT_ID = UUID("30000000-0000-0000-0000-000000000001")
ROAD_A_ID = UUID("30000000-0000-0000-0000-000000000010")
ROAD_B_ID = UUID("30000000-0000-0000-0000-000000000011")


def _plot() -> Plot:
    return create_rectangular_plot(
        plot_id=PLOT_ID,
        width_value=40,
        width_unit=LengthUnit.FT,
        depth_value=60,
        depth_unit=LengthUnit.FT,
    )


def test_corner_plot_supports_two_distinct_road_edges() -> None:
    plot = _plot()
    first = create_road(
        plot=plot,
        road_id=ROAD_A_ID,
        name="Road A",
        plot_edge_ids=(plot.edge_ids[0],),
        width_mm=9_000,
        primary_access=True,
    )
    second = create_road(
        plot=plot,
        road_id=ROAD_B_ID,
        name="Road B",
        plot_edge_ids=(plot.edge_ids[1],),
        width_mm=12_000,
    )

    result = validate_road_set(plot, (first, second))

    assert result.road_count == 2
    assert result.referenced_edge_count == 2
    assert result.primary_access_road_id == ROAD_A_ID


def test_unknown_edge_is_rejected() -> None:
    plot = _plot()
    unknown = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")

    with pytest.raises(UnknownPlotEdgeError):
        create_road(
            plot=plot,
            road_id=ROAD_A_ID,
            plot_edge_ids=(unknown,),
        )


def test_same_whole_edge_cannot_be_assigned_to_two_roads() -> None:
    plot = _plot()
    first = create_road(
        plot=plot,
        road_id=ROAD_A_ID,
        plot_edge_ids=(plot.edge_ids[0],),
    )
    second = create_road(
        plot=plot,
        road_id=ROAD_B_ID,
        plot_edge_ids=(plot.edge_ids[0],),
    )

    with pytest.raises(InvalidRoadDefinitionError, match="multiple roads"):
        validate_road_set(plot, (first, second))


def test_primary_access_is_not_implicitly_assigned_to_multiple_roads() -> None:
    plot = _plot()
    first = create_road(
        plot=plot,
        road_id=ROAD_A_ID,
        plot_edge_ids=(plot.edge_ids[0],),
        primary_access=True,
    )
    second = create_road(
        plot=plot,
        road_id=ROAD_B_ID,
        plot_edge_ids=(plot.edge_ids[1],),
        primary_access=True,
    )

    with pytest.raises(InvalidRoadDefinitionError, match="At most one road"):
        validate_road_set(plot, (first, second))
