from uuid import UUID

import pytest

from ai_vastu.plan_schema import IntPoint, PlotInputSource, VerificationStatus
from ai_vastu.plot import (
    PlotDefinitionError,
    SurveyQuadrilateralDefinition,
    UnderdeterminedPlotError,
    UnsupportedSurveyDefinitionError,
    create_polygon_plot,
    create_survey_quadrilateral,
    make_closure_report,
    signed_double_area,
)

PLOT_ID = UUID("20000000-0000-0000-0000-000000000001")


def test_verified_polygon_preserves_authoritative_coordinates() -> None:
    vertices = (
        IntPoint(x_mm=0, y_mm=0),
        IntPoint(x_mm=8_000, y_mm=0),
        IntPoint(x_mm=7_500, y_mm=12_000),
        IntPoint(x_mm=500, y_mm=11_500),
    )
    plot = create_polygon_plot(
        plot_id=PLOT_ID,
        vertices=vertices,
        input_source=PlotInputSource.SURVEY,
        verification_status=VerificationStatus.SURVEY_VERIFIED,
    )

    assert plot.boundary.outer == vertices
    assert len(plot.edge_ids) == 4
    assert signed_double_area(vertices) > 0


def test_four_side_lengths_alone_fail_closed_as_underdetermined() -> None:
    definition = SurveyQuadrilateralDefinition(
        side_lengths_mm=(9_000, 12_000, 8_700, 11_800),
    )

    with pytest.raises(UnderdeterminedPlotError, match="do not uniquely determine"):
        create_survey_quadrilateral(plot_id=PLOT_ID, definition=definition)


def test_unsolved_diagonal_or_bearing_evidence_is_not_silently_invented() -> None:
    definition = SurveyQuadrilateralDefinition(
        side_lengths_mm=(9_000, 12_000, 8_700, 11_800),
        diagonal_mm=14_500,
    )

    with pytest.raises(UnsupportedSurveyDefinitionError, match="does not yet solve"):
        create_survey_quadrilateral(plot_id=PLOT_ID, definition=definition)


def test_survey_coordinates_create_authoritative_polygon() -> None:
    coordinates = (
        IntPoint(x_mm=0, y_mm=0),
        IntPoint(x_mm=9_000, y_mm=0),
        IntPoint(x_mm=8_700, y_mm=11_800),
        IntPoint(x_mm=0, y_mm=12_000),
    )
    definition = SurveyQuadrilateralDefinition(
        side_lengths_mm=(9_000, 12_000, 8_700, 11_800),
        corner_coordinates=coordinates,
    )
    plot = create_survey_quadrilateral(plot_id=PLOT_ID, definition=definition)

    assert plot.boundary.outer == coordinates
    assert [item.label for item in plot.declared_measurements] == [
        "side_1",
        "side_2",
        "side_3",
        "side_4",
    ]


def test_closure_report_preserves_37_mm_discrepancy() -> None:
    expected = IntPoint(x_mm=0, y_mm=0)
    observed = IntPoint(x_mm=37, y_mm=0)

    rejected = make_closure_report(
        expected_close=expected,
        observed_close=observed,
        tolerance_mm=20,
    )
    accepted = make_closure_report(
        expected_close=expected,
        observed_close=observed,
        tolerance_mm=40,
    )

    assert rejected.closure_error_mm == 37
    assert rejected.accepted is False
    assert accepted.accepted is True


def test_polygon_rejects_zero_length_boundary_edge() -> None:
    vertices = (
        IntPoint(x_mm=0, y_mm=0),
        IntPoint(x_mm=5_000, y_mm=0),
        IntPoint(x_mm=5_000, y_mm=0),
        IntPoint(x_mm=0, y_mm=5_000),
    )

    with pytest.raises(PlotDefinitionError, match="zero-length edge"):
        create_polygon_plot(
            plot_id=PLOT_ID,
            vertices=vertices,
            input_source=PlotInputSource.INTERACTIVE,
            verification_status=VerificationStatus.UNVERIFIED,
        )
