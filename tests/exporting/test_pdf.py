from __future__ import annotations

from ai_vastu.exporting import PdfExportConfig, build_drawing_scene, render_pdf

from .helpers import export_plan


def test_pdf_export_is_vector_pdf_and_invariant() -> None:
    scene = build_drawing_scene(export_plan())
    config = PdfExportConfig(page_size="A4_LANDSCAPE", margin_mm=10, title_block_height_mm=15)
    first = render_pdf(scene, config)
    second = render_pdf(scene, config)
    assert first.content.startswith(b"%PDF-")
    assert first.content == second.content
    assert first.scene_hash == scene.scene_hash
    assert b"Ground Floor" in first.content
