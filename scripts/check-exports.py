from export_smoke_fixture import export_smoke_plan

from ai_vastu.exporting import (
    DxfExportConfig,
    PdfExportConfig,
    RasterExportConfig,
    export_plan_bundle,
)

plan = export_smoke_plan()
config_raster = RasterExportConfig(width_px=1_200, height_px=900, margin_px=40, jpeg_quality=90)
config_pdf = PdfExportConfig(page_size="A4_LANDSCAPE", margin_mm=10, title_block_height_mm=15)
config_dxf = DxfExportConfig()
first = export_plan_bundle(plan, raster=config_raster, pdf=config_pdf, dxf=config_dxf)
second = export_plan_bundle(plan, raster=config_raster, pdf=config_pdf, dxf=config_dxf)

assert first.scene.scene_hash == second.scene.scene_hash
assert first.jpeg.content == second.jpeg.content
assert first.pdf.content == second.pdf.content
assert first.dxf.content == second.dxf.content
assert first.jpeg.content.startswith(b"\xff\xd8")
assert first.pdf.content.startswith(b"%PDF-")
assert b"SECTION" in first.dxf.content

print(
    "Exports deterministic: "
    f"scene={first.scene.scene_hash}, "
    f"jpg={len(first.jpeg.content)}B, "
    f"pdf={len(first.pdf.content)}B, "
    f"dxf={len(first.dxf.content)}B"
)
