from __future__ import annotations

from ai_vastu.exporting import build_drawing_scene
from ai_vastu.exporting.geometry import opening_segments, visible_wall_segments

from .helpers import WALL_IDS, export_plan


def test_drawing_scene_is_hash_stable_and_source_bound() -> None:
    document = export_plan()
    first = build_drawing_scene(document)
    second = build_drawing_scene(document)
    assert first.scene_hash == second.scene_hash
    assert first.source_plan_hash == document.compute_content_hash()
    assert first.floor_id == document.floors[0].id


def test_wall_opening_is_exported_as_a_real_gap() -> None:
    scene = build_drawing_scene(export_plan())
    partition = [item for item in visible_wall_segments(scene) if item.wall_id == WALL_IDS[4]]
    assert len(partition) == 2
    assert partition[0].start == (5_000.0, 0.0)
    assert partition[0].end == (5_000.0, 2_000.0)
    assert partition[1].start == (5_000.0, 2_900.0)
    assert partition[1].end == (5_000.0, 8_000.0)
    opening = opening_segments(scene)
    assert opening[0].start == (5_000.0, 2_000.0)
    assert opening[0].end == (5_000.0, 2_900.0)
