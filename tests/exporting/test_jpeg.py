from __future__ import annotations

from io import BytesIO

from PIL import Image

from ai_vastu.exporting import RasterExportConfig, build_drawing_scene, render_jpeg

from .helpers import export_plan


def test_jpeg_export_uses_requested_pixel_canvas() -> None:
    scene = build_drawing_scene(export_plan())
    config = RasterExportConfig(width_px=1_200, height_px=900, margin_px=40, jpeg_quality=90)
    first = render_jpeg(scene, config)
    second = render_jpeg(scene, config)
    assert first.content[:2] == b"\xff\xd8"
    assert first.scene_hash == scene.scene_hash
    assert first.content == second.content
    image = Image.open(BytesIO(first.content))
    assert image.size == (1_200, 900)
