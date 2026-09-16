from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema import PlanDocument

from .dxf_exporter import render_dxf
from .jpeg_exporter import render_jpeg
from .models import DxfExportConfig, ExportBundle, PdfExportConfig, RasterExportConfig
from .pdf_exporter import render_pdf
from .scene import build_drawing_scene


def export_plan_bundle(
    document: PlanDocument,
    *,
    floor_id: UUID | None = None,
    raster: RasterExportConfig | None = None,
    pdf: PdfExportConfig | None = None,
    dxf: DxfExportConfig | None = None,
) -> ExportBundle:
    scene = build_drawing_scene(document, floor_id=floor_id)
    raster_config = raster or RasterExportConfig()
    pdf_config = pdf or PdfExportConfig()
    dxf_config = dxf or DxfExportConfig()
    return ExportBundle(
        scene=scene,
        jpeg=render_jpeg(scene, raster_config),
        pdf=render_pdf(scene, pdf_config),
        dxf=render_dxf(scene, dxf_config),
    )
