from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema import PlanDocument

from .dxf_exporter import render_dxf
from .jpeg_exporter import render_jpeg
from .models import (
    DxfExportConfig,
    ExportBundle,
    PdfExportConfig,
    RasterExportConfig,
    SvgExportConfig,
)
from .pdf_exporter import render_pdf
from .scene import build_drawing_scene
from .svg_exporter import render_svg


def export_plan_bundle(
    document: PlanDocument,
    *,
    floor_id: UUID | None = None,
    svg: SvgExportConfig | None = None,
    raster: RasterExportConfig | None = None,
    pdf: PdfExportConfig | None = None,
    dxf: DxfExportConfig | None = None,
) -> ExportBundle:
    scene = build_drawing_scene(document, floor_id=floor_id)
    svg_config = svg or SvgExportConfig()
    raster_config = raster or RasterExportConfig()
    pdf_config = pdf or PdfExportConfig()
    dxf_config = dxf or DxfExportConfig()
    return ExportBundle(
        scene=scene,
        svg=render_svg(scene, svg_config),
        jpeg=render_jpeg(scene, raster_config),
        pdf=render_pdf(scene, pdf_config),
        dxf=render_dxf(scene, dxf_config),
    )


def export_all_floor_bundles(
    document: PlanDocument,
    *,
    svg: SvgExportConfig | None = None,
    raster: RasterExportConfig | None = None,
    pdf: PdfExportConfig | None = None,
    dxf: DxfExportConfig | None = None,
) -> tuple[ExportBundle, ...]:
    """Render every canonical floor independently in stable floor order."""
    return tuple(
        export_plan_bundle(
            document,
            floor_id=floor.id,
            svg=svg,
            raster=raster,
            pdf=pdf,
            dxf=dxf,
        )
        for floor in sorted(document.floors, key=lambda item: item.index)
    )
