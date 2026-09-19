from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema import (
    BuildableArea,
    Floor,
    GenerationMetadata,
    IntPoint,
    IntPolygon,
    Orientation,
    OrientationSource,
    PlanDocument,
    Plot,
    PlotGeometryType,
    PlotInputSource,
    ScoringSummary,
    ValidationReport,
    VastuAnalysis,
    VerificationStatus,
)

PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
REVISION_ID = UUID("22222222-2222-2222-2222-222222222222")
PLOT_ID = UUID("33333333-3333-3333-3333-333333333333")
FLOOR_ID = UUID("44444444-4444-4444-4444-444444444444")
EDGE_IDS = tuple(
    UUID(value)
    for value in (
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1",
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2",
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3",
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4",
    )
)


def rectangle() -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=9_144, y_mm=0),
            IntPoint(x_mm=9_144, y_mm=15_240),
            IntPoint(x_mm=0, y_mm=15_240),
        )
    )


def sample_plan() -> PlanDocument:
    boundary = rectangle()
    return PlanDocument(
        schema_version="1.1.0",
        project_id=PROJECT_ID,
        revision_id=REVISION_ID,
        canonical_units="mm",
        plot=Plot(
            id=PLOT_ID,
            geometry_type=PlotGeometryType.RECTANGLE,
            boundary=boundary,
            edge_ids=EDGE_IDS,
            input_source=PlotInputSource.MANUAL,
            verification_status=VerificationStatus.USER_VERIFIED,
        ),
        orientation=Orientation(
            north_rotation_udeg=0,
            source=OrientationSource.USER,
            verified=True,
        ),
        buildable_area=BuildableArea(polygon=boundary),
        floors=(
            Floor(
                id=FLOOR_ID,
                index=0,
                name="Ground Floor",
                elevation_mm=0,
                floor_to_floor_mm=3_300,
                boundary=boundary,
            ),
        ),
        vastu_spec_version="UNFROZEN",
        vastu_analysis=VastuAnalysis(spec_version="UNFROZEN"),
        validation=ValidationReport(valid=True),
        scoring=ScoringSummary(mode="UNSCORED", overall_basis_points=0),
        generation_metadata=GenerationMetadata(),
    )
