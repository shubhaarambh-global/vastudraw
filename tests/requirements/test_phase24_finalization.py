from pathlib import Path
from uuid import UUID

from ai_vastu.plan_schema.geometry import IntPoint, IntPolygon
from ai_vastu.plan_schema.models import Floor, RoomGeometry, RoomType
from ai_vastu.requirements.finalization import (
    EXPECTED_VASTU_V1_BUNDLE_HASH,
    _road_edge_index,
    _sector_for_point,
    build_vastu_analysis,
    load_production_vastu_bundle,
)


def rectangle(x1: int, y1: int, x2: int, y2: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x2, y_mm=y1),
            IntPoint(x_mm=x2, y_mm=y2),
            IntPoint(x_mm=x1, y_mm=y2),
        )
    )


def test_true_north_sector_classifier_at_zero_rotation() -> None:
    plot = rectangle(0, 0, 10000, 10000)
    assert (
        _sector_for_point(
            x_mm=7500,
            y_mm=7500,
            plot=plot,
            north_rotation_udeg=0,
        )
        == "NE"
    )
    assert (
        _sector_for_point(
            x_mm=7500,
            y_mm=2500,
            plot=plot,
            north_rotation_udeg=0,
        )
        == "SE"
    )


def test_cardinal_road_edges_at_zero_rotation() -> None:
    assert _road_edge_index("S", 0) == 0
    assert _road_edge_index("E", 0) == 1
    assert _road_edge_index("N", 0) == 2
    assert _road_edge_index("W", 0) == 3


def test_frozen_vastu_v1_evaluates_reviewed_centroid_rules() -> None:
    bundle = load_production_vastu_bundle()
    assert bundle.content_hash == EXPECTED_VASTU_V1_BUNDLE_HASH
    assert len(bundle.rules) == 4

    plot = rectangle(0, 0, 10000, 10000)
    rooms = (
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            room_type=RoomType("kitchen"),
            polygon=rectangle(7000, 2000, 8000, 3000),
        ),
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            room_type=RoomType("puja"),
            polygon=rectangle(7000, 7000, 8000, 8000),
        ),
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            room_type=RoomType("master_bedroom"),
            polygon=rectangle(4500, 2000, 5500, 3000),
        ),
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000004"),
            room_type=RoomType("bath"),
            polygon=rectangle(7000, 4500, 8000, 5500),
        ),
    )
    floor = Floor(
        id=UUID("00000000-0000-0000-0000-000000000010"),
        index=0,
        name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3000,
        boundary=plot,
        rooms=rooms,
    )
    analysis = build_vastu_analysis(
        bundle=bundle,
        floor=floor,
        plot_boundary=plot,
        north_rotation_udeg=0,
    )
    assert analysis.spec_version == "1.0.0"
    assert len(analysis.results) == 4
    assert all(result.status.value == "PASS" for result in analysis.results)


def test_phase24_bundle_is_repository_backed() -> None:
    bundle_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "vastu"
        / "spec-v1.0"
        / "production"
        / "rule-bundle.json"
    )
    assert bundle_path.is_file()
