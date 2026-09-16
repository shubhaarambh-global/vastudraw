from __future__ import annotations

from ai_vastu.architectural_geometry import build_architectural_geometry
from ai_vastu.plan_schema import WallCategory

from .helpers import build_request


def test_solver_placements_become_exact_room_polygons() -> None:
    request = build_request()
    built = build_architectural_geometry(request)
    placement_index = {item.room_instance_id: item for item in request.planner_result.placements}
    assert len(built.floor.rooms) == len(placement_index)
    for room in built.floor.rooms:
        placement = placement_index[room.id]
        xs = [point.x_mm for point in room.polygon.outer]
        ys = [point.y_mm for point in room.polygon.outer]
        assert min(xs) == placement.x_mm
        assert max(xs) == placement.x_mm + placement.width_mm
        assert min(ys) == placement.y_mm
        assert max(ys) == placement.y_mm + placement.depth_mm


def test_wall_segments_are_unique_and_deterministic() -> None:
    request = build_request()
    first = build_architectural_geometry(request)
    second = build_architectural_geometry(request)
    assert first.content_hash == second.content_hash
    assert first.floor == second.floor
    signatures = {
        (
            wall.axis.start.x_mm,
            wall.axis.start.y_mm,
            wall.axis.end.x_mm,
            wall.axis.end.y_mm,
        )
        for wall in first.floor.walls
    }
    assert len(signatures) == len(first.floor.walls)
    assert {wall.category for wall in first.floor.walls} <= {
        WallCategory.EXTERNAL,
        WallCategory.INTERNAL,
    }


def test_wall_thickness_is_explicit_not_defaulted() -> None:
    built = build_architectural_geometry(build_request())
    for wall in built.floor.walls:
        expected = 230 if wall.category is WallCategory.EXTERNAL else 115
        assert wall.thickness_mm == expected


def test_builder_emits_wall_clearance_provenance_notice() -> None:
    built = build_architectural_geometry(build_request())
    assert {notice.code for notice in built.notices} == {
        "ROOM_ENVELOPES_PRECEDE_WALL_CLEARANCE_VALIDATION"
    }


def test_t_junction_splits_shared_partition_at_junction() -> None:
    from .helpers import t_junction_request

    built = build_architectural_geometry(t_junction_request())
    shared = [
        wall
        for wall in built.floor.walls
        if wall.axis.start.x_mm == 3000 and wall.axis.end.x_mm == 3000
    ]
    intervals = sorted((wall.axis.start.y_mm, wall.axis.end.y_mm) for wall in shared)
    assert intervals == [(0, 2000), (2000, 4000)]
