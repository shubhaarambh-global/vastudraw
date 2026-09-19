from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema import (
    Annotation,
    AxisSegment,
    BuildableArea,
    Dimension,
    Floor,
    GenerationMetadata,
    IntPoint,
    IntPolygon,
    Opening,
    OpeningKind,
    Orientation,
    OrientationSource,
    PlanDocument,
    Plot,
    PlotGeometryType,
    PlotInputSource,
    RoomGeometry,
    RoomType,
    ScoringSummary,
    ValidationReport,
    VastuAnalysis,
    VerificationStatus,
    Wall,
    WallCategory,
)

PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
REVISION_ID = UUID("22222222-2222-2222-2222-222222222222")
FLOOR_ID = UUID("44444444-4444-4444-4444-444444444444")
PLOT_ID = UUID("33333333-3333-3333-3333-333333333333")
EDGE_IDS = tuple(UUID(f"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa{i}") for i in range(1, 5))
ROOM_A = UUID("55555555-5555-5555-5555-555555555551")
ROOM_B = UUID("55555555-5555-5555-5555-555555555552")
WALL_IDS = tuple(UUID(f"66666666-6666-6666-6666-66666666666{i}") for i in range(1, 6))
OPENING_ID = UUID("77777777-7777-7777-7777-777777777777")
DIM_ID = UUID("88888888-8888-8888-8888-888888888888")
ANNOTATION_ID = UUID("99999999-9999-9999-9999-999999999999")


def rectangle(x0: int, y0: int, x1: int, y1: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x0, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x0, y_mm=y1),
        )
    )


def export_plan() -> PlanDocument:
    boundary = rectangle(0, 0, 10_000, 8_000)
    rooms = (
        RoomGeometry(
            id=ROOM_A,
            room_type=RoomType.LIVING,
            name="Living",
            polygon=rectangle(0, 0, 5_000, 8_000),
        ),
        RoomGeometry(
            id=ROOM_B,
            room_type=RoomType.KITCHEN,
            name="Kitchen",
            polygon=rectangle(5_000, 0, 10_000, 8_000),
        ),
    )
    walls = (
        Wall(
            id=WALL_IDS[0],
            axis=AxisSegment(
                start=IntPoint(x_mm=0, y_mm=0),
                end=IntPoint(x_mm=10_000, y_mm=0),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[1],
            axis=AxisSegment(
                start=IntPoint(x_mm=10_000, y_mm=0),
                end=IntPoint(x_mm=10_000, y_mm=8_000),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[2],
            axis=AxisSegment(
                start=IntPoint(x_mm=10_000, y_mm=8_000),
                end=IntPoint(x_mm=0, y_mm=8_000),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[3],
            axis=AxisSegment(
                start=IntPoint(x_mm=0, y_mm=8_000),
                end=IntPoint(x_mm=0, y_mm=0),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[4],
            axis=AxisSegment(
                start=IntPoint(x_mm=5_000, y_mm=0),
                end=IntPoint(x_mm=5_000, y_mm=8_000),
            ),
            thickness_mm=115,
            height_mm=3_000,
            category=WallCategory.INTERNAL,
        ),
    )
    opening = Opening(
        id=OPENING_ID,
        wall_id=WALL_IDS[4],
        kind=OpeningKind.DOOR,
        offset_from_wall_start_mm=2_000,
        width_mm=900,
        height_mm=2_100,
    )
    floor = Floor(
        id=FLOOR_ID,
        index=0,
        name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3_300,
        boundary=boundary,
        rooms=rooms,
        walls=walls,
        openings=(opening,),
        dimensions=(
            Dimension(
                id=DIM_ID,
                start=IntPoint(x_mm=0, y_mm=0),
                end=IntPoint(x_mm=10_000, y_mm=0),
                offset_mm=600,
            ),
        ),
        annotations=(
            Annotation(
                id=ANNOTATION_ID,
                anchor=IntPoint(x_mm=300, y_mm=7_500),
                text="GROUND FLOOR",
                category="title",
            ),
        ),
    )
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
        floors=(floor,),
        vastu_spec_version="UNFROZEN",
        vastu_analysis=VastuAnalysis(spec_version="UNFROZEN"),
        validation=ValidationReport(valid=True),
        scoring=ScoringSummary(mode="UNSCORED", overall_basis_points=0),
        generation_metadata=GenerationMetadata(),
    ).with_content_hash()
