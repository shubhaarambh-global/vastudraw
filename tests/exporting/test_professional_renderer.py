from __future__ import annotations

from io import StringIO
from uuid import UUID

import ezdxf

from ai_vastu.exporting import (
    EXPORT_SCENE_VERSION,
    DimensionDisplayUnit,
    DxfExportConfig,
    PdfExportConfig,
    RasterExportConfig,
    build_drawing_scene,
    build_professional_presentation,
    export_all_floor_bundles,
    render_dxf,
    render_jpeg,
    render_pdf,
)
from ai_vastu.exporting.geometry import polygon_bounds, visible_wall_segments
from ai_vastu.plan_schema import (
    Floor,
    Opening,
    OpeningKind,
    PurposefulSiteSpace,
    RoomGeometry,
    RoomType,
    SiteSpaceKind,
    Stair,
    StairType,
)

from .helpers import WALL_IDS, export_plan, rectangle


def _id(value: int) -> UUID:
    return UUID(f"bbbbbbbb-bbbb-bbbb-bbbb-{value:012d}")


def professional_plan(*, floors: int = 1):
    document = export_plan()
    base = document.floors[0]
    rooms = (
        RoomGeometry(
            id=_id(1),
            room_type=RoomType.LIVING,
            name="Living",
            polygon=rectangle(0, 0, 5_000, 4_000),
        ),
        RoomGeometry(
            id=_id(2), room_type=RoomType.KITCHEN, polygon=rectangle(5_000, 0, 8_000, 4_000)
        ),
        RoomGeometry(
            id=_id(3), room_type=RoomType.COMMON_TOILET, polygon=rectangle(8_000, 0, 10_000, 4_000)
        ),
        RoomGeometry(
            id=_id(4), room_type=RoomType.PARKING, polygon=rectangle(0, 4_000, 3_000, 8_000)
        ),
        RoomGeometry(
            id=_id(5), room_type=RoomType.STAIRCASE, polygon=rectangle(3_000, 4_000, 5_300, 8_000)
        ),
        RoomGeometry(
            id=_id(6), room_type=RoomType.BEDROOM, polygon=rectangle(5_300, 4_000, 10_000, 8_000)
        ),
    )
    openings = (
        base.openings[0],
        Opening(
            id=_id(10),
            wall_id=WALL_IDS[2],
            kind=OpeningKind.WINDOW,
            offset_from_wall_start_mm=2_000,
            width_mm=1_500,
            height_mm=1_200,
            sill_height_mm=900,
        ),
    )
    stair = Stair(
        id=_id(11),
        stair_type=StairType.DOG_LEGGED,
        footprint=rectangle(3_000, 4_000, 5_300, 8_000),
        width_mm=1_000,
        riser_mm=150,
        tread_mm=270,
        number_of_risers=20,
        floor_height_mm=3_000,
        landing_depth_mm=1_000,
        direction_udeg=0,
        headroom_mm=2_100,
    )
    spaces = (
        PurposefulSiteSpace(
            id=_id(12),
            kind=SiteSpaceKind.LANDSCAPE,
            polygon=rectangle(0, 0, 700, 8_000),
            label="Garden",
        ),
        PurposefulSiteSpace(
            id=_id(13),
            kind=SiteSpaceKind.VEHICLE_ACCESS,
            polygon=rectangle(700, 0, 3_000, 900),
        ),
    )
    built_floors = []
    for index in range(floors):
        built_floors.append(
            Floor(
                **base.model_dump(
                    exclude={
                        "id",
                        "index",
                        "name",
                        "elevation_mm",
                        "rooms",
                        "site_spaces",
                        "openings",
                        "stairs",
                    }
                ),
                id=_id(100 + index),
                index=index,
                name=("Ground Floor" if index == 0 else f"Floor {index}"),
                elevation_mm=index * base.floor_to_floor_mm,
                rooms=tuple(
                    room.model_copy(update={"id": _id(index * 20 + offset + 1)})
                    for offset, room in enumerate(rooms)
                ),
                site_spaces=spaces if index == 0 else (),
                openings=openings,
                stairs=(stair.model_copy(update={"id": _id(200 + index)}),),
            )
        )
    return document.model_copy(
        update={"floors": tuple(built_floors), "content_hash": None}
    ).with_content_hash()


def test_scene_1_1_projects_canonical_site_spaces_without_mutating_plan() -> None:
    document = professional_plan()
    before = document.to_canonical_json()
    first = build_drawing_scene(document)
    second = build_drawing_scene(document)
    assert EXPORT_SCENE_VERSION == "1.1.0"
    assert first.version == "1.1.0"
    assert [space.kind for space in first.site_spaces] == [
        SiteSpaceKind.LANDSCAPE,
        SiteSpaceKind.VEHICLE_ACCESS,
    ]
    assert first == second
    assert document.to_canonical_json() == before
    assert first.source_plan_hash == document.compute_content_hash()


def test_wall_linework_retains_real_thickness_and_opening_gaps() -> None:
    scene = build_drawing_scene(professional_plan())
    segments = visible_wall_segments(scene)
    external = next(item for item in segments if item.wall_id == WALL_IDS[0])
    internal = next(item for item in segments if item.wall_id == WALL_IDS[4])
    assert external.thickness_mm == 230
    assert internal.thickness_mm == 115
    assert len([item for item in segments if item.wall_id == WALL_IDS[4]]) == 2


def test_opening_symbols_are_canonical_only_and_deterministic() -> None:
    scene = build_drawing_scene(professional_plan())
    first = build_professional_presentation(scene)
    second = build_professional_presentation(scene)
    assert first == second
    assert len(first.doors) == 1
    assert len(first.windows) == 1
    assert first.doors[0].derived_swing
    assert len(first.doors[0].swing_arc) == 9
    assert len(first.windows[0].lines) == 3

    no_openings = scene.model_copy(update={"openings": (), "scene_hash": None})
    empty = build_professional_presentation(no_openings)
    assert empty.doors == ()
    assert empty.windows == ()


def test_stair_uses_canonical_footprint_with_treads_landing_and_direction() -> None:
    scene = build_drawing_scene(professional_plan())
    presentation = build_professional_presentation(scene)
    graphic = presentation.stairs[0]
    assert graphic.outline == scene.stairs[0].footprint
    assert len(graphic.treads) >= 4
    assert graphic.landing is not None
    assert graphic.flight_divider is not None
    assert graphic.arrow.start != graphic.arrow.end
    assert graphic.direction_label == "UP"


def test_labels_dimensions_orientation_and_scale_evidence_are_honest() -> None:
    scene = build_drawing_scene(professional_plan())
    presentation = build_professional_presentation(
        scene,
        dimension_unit=DimensionDisplayUnit.METRES,
    )
    assert {item.title for item in presentation.room_labels} >= {
        "LIVING",
        "KITCHEN",
        "COMMON TOILET",
        "PARKING",
        "STAIRCASE",
        "BEDROOM",
    }
    assert all("m" in item.dimension for item in presentation.room_labels)
    assert len([item for item in presentation.dimensions if item.category == "site"]) == 2
    assert scene.north_rotation_udeg == 0


def test_presentation_furniture_fixtures_and_vehicle_stay_inside_owner_room() -> None:
    scene = build_drawing_scene(professional_plan())
    presentation = build_professional_presentation(scene)
    rooms = {room.id: polygon_bounds(room.polygon) for room in scene.rooms}
    kinds = {symbol.kind for symbol in presentation.symbols}
    assert {"sofa", "kitchen-counter", "sanitary", "vehicle", "bed"} <= kinds
    for symbol in presentation.symbols:
        room = rooms[symbol.owner_room_id]
        x0, y0, x1, y1 = symbol.bounds
        assert room.min_x_mm <= x0 < x1 <= room.max_x_mm
        assert room.min_y_mm <= y0 < y1 <= room.max_y_mm


def test_multi_floor_exports_every_floor_and_aligned_stairs_remain_aligned() -> None:
    document = professional_plan(floors=2)
    bundles = export_all_floor_bundles(
        document,
        raster=RasterExportConfig(width_px=800, height_px=600),
        pdf=PdfExportConfig(page_size="A4_LANDSCAPE"),
    )
    assert [bundle.scene.floor_index for bundle in bundles] == [0, 1]
    assert [bundle.scene.floor_id for bundle in bundles] == [floor.id for floor in document.floors]
    assert bundles[0].scene.stairs[0].footprint == bundles[1].scene.stairs[0].footprint
    assert bundles[0].jpeg.filename != bundles[1].jpeg.filename


def test_pdf_jpeg_and_dxf_share_professional_semantics_deterministically() -> None:
    scene = build_drawing_scene(professional_plan())
    jpeg_config = RasterExportConfig(width_px=1_200, height_px=900)
    pdf_config = PdfExportConfig(page_size="A4_LANDSCAPE")
    dxf_config = DxfExportConfig(dimension_unit=DimensionDisplayUnit.METRES)
    assert render_jpeg(scene, jpeg_config).content == render_jpeg(scene, jpeg_config).content
    pdf = render_pdf(scene, pdf_config)
    assert pdf.content == render_pdf(scene, pdf_config).content
    assert b"VASTUDRAW" in pdf.content
    assert b"COMMON TOILET" in pdf.content
    dxf = render_dxf(scene, dxf_config)
    assert dxf.content == render_dxf(scene, dxf_config).content
    drawing = ezdxf.read(StringIO(dxf.content.decode("utf-8")))
    assert "AIA_SITE" in drawing.layers
    assert "AIA_DOOR" in drawing.layers
    assert "AIA_WINDOW" in drawing.layers
    assert "AIA_STAIR_TREAD" in drawing.layers
    modelspace = drawing.modelspace()
    assert len(modelspace.query('LINE[layer=="AIA_DOOR"]')) == 1
    assert len(modelspace.query('LINE[layer=="AIA_WINDOW"]')) == 3
    assert len(modelspace.query('LINE[layer=="AIA_STAIR_TREAD"]')) >= 4


def test_candidate_documents_render_their_own_geometry() -> None:
    first = professional_plan()
    second_floor = first.floors[0].model_copy(
        update={
            "rooms": tuple(
                room.model_copy(update={"polygon": rectangle(0, 0, 4_500, 4_000)})
                if room.room_type is RoomType.LIVING
                else room
                for room in first.floors[0].rooms
            )
        }
    )
    second = first.model_copy(update={"floors": (second_floor,), "content_hash": None})
    first_label = next(
        item
        for item in build_professional_presentation(build_drawing_scene(first)).room_labels
        if item.title == "LIVING"
    )
    second_label = next(
        item
        for item in build_professional_presentation(build_drawing_scene(second)).room_labels
        if item.title == "LIVING"
    )
    assert first_label.dimension != second_label.dimension
