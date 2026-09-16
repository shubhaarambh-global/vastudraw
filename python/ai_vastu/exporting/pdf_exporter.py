from __future__ import annotations

from io import BytesIO
from math import cos, hypot, radians, sin

from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from ai_vastu.plan_schema import IntPoint

from .geometry import (
    offset_segment,
    opening_segments,
    polygon_center,
    scene_bounds,
    visible_wall_segments,
)
from .models import DrawingScene, ExportArtifact, PdfExportConfig


class _PdfTransform:
    def __init__(
        self,
        scene: DrawingScene,
        config: PdfExportConfig,
        page_width: float,
        page_height: float,
    ) -> None:
        bounds = scene_bounds(scene)
        margin = config.margin_mm * mm
        title = config.title_block_height_mm * mm
        usable_width = max(1.0, page_width - 2 * margin)
        usable_height = max(1.0, page_height - 2 * margin - title)
        self.scale = min(
            usable_width / max(bounds.width_mm, 1.0),
            usable_height / max(bounds.height_mm, 1.0),
        )
        drawn_width = bounds.width_mm * self.scale
        drawn_height = bounds.height_mm * self.scale
        self.left = margin + (usable_width - drawn_width) / 2.0
        self.bottom = margin + title + (usable_height - drawn_height) / 2.0
        self.min_x = bounds.min_x_mm
        self.min_y = bounds.min_y_mm

    def point(self, value: tuple[float, float]) -> tuple[float, float]:
        return (
            self.left + (value[0] - self.min_x) * self.scale,
            self.bottom + (value[1] - self.min_y) * self.scale,
        )


def _draw_polygon(
    canvas: Canvas,
    points: tuple[IntPoint, ...],
    transform: _PdfTransform,
    *,
    line_width: float = 0.7,
) -> None:
    if not points:
        return
    path = canvas.beginPath()
    first = points[0]
    first_xy = transform.point((first.x_mm, first.y_mm))
    path.moveTo(*first_xy)
    for point in points[1:]:
        path.lineTo(*transform.point((point.x_mm, point.y_mm)))
    path.close()
    canvas.setLineWidth(line_width)
    canvas.drawPath(path, stroke=1, fill=0)


def render_pdf(scene: DrawingScene, config: PdfExportConfig) -> ExportArtifact:
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()
    page = landscape(A3 if config.page_size == "A3_LANDSCAPE" else A4)
    page_width, page_height = page
    transform = _PdfTransform(scene, config, page_width, page_height)
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=page, invariant=1, pageCompression=0)
    canvas.setTitle(f"AI Vastu Architect - {scene.floor_name}")
    canvas.setCreator("AI Vastu Architect")

    canvas.setStrokeGray(0.65)
    _draw_polygon(canvas, scene.plot_boundary.outer, transform, line_width=0.6)
    canvas.setStrokeGray(0.75)
    canvas.setDash(4, 3)
    _draw_polygon(canvas, scene.buildable_boundary.outer, transform, line_width=0.6)
    canvas.setDash()
    canvas.setStrokeGray(0.25)
    _draw_polygon(canvas, scene.floor_boundary.outer, transform, line_width=1.0)

    for room in scene.rooms:
        canvas.setStrokeGray(0.45)
        _draw_polygon(canvas, room.polygon.outer, transform, line_width=0.45)
        if config.show_room_labels:
            center = transform.point(polygon_center(room.polygon))
            label = room.name or room.room_type.value.replace("_", " ").title()
            canvas.setFillGray(0.25)
            canvas.setFont("Helvetica", 7)
            canvas.drawCentredString(center[0], center[1] - 2.5, label)

    canvas.setLineCap(2)
    canvas.setStrokeGray(0.08)
    for segment in visible_wall_segments(scene):
        start = transform.point(segment.start)
        end = transform.point(segment.end)
        canvas.setLineWidth(max(0.4, segment.thickness_mm * transform.scale))
        canvas.line(start[0], start[1], end[0], end[1])

    canvas.setStrokeColorRGB(0.07, 0.55, 0.32)
    canvas.setLineWidth(1.2)
    for opening in opening_segments(scene):
        start = transform.point(opening.start)
        end = transform.point(opening.end)
        canvas.line(start[0], start[1], end[0], end[1])

    canvas.setStrokeGray(0.35)
    for stair in scene.stairs:
        _draw_polygon(canvas, stair.footprint.outer, transform, line_width=0.6)
    for furniture in scene.furniture:
        _draw_polygon(canvas, furniture.footprint.outer, transform, line_width=0.35)

    if config.show_dimensions:
        canvas.setStrokeGray(0.4)
        canvas.setFillGray(0.3)
        canvas.setFont("Helvetica", 6.5)
        for dimension in scene.dimensions:
            start, end = offset_segment(dimension.start, dimension.end, dimension.offset_mm)
            p1 = transform.point(start)
            p2 = transform.point(end)
            canvas.setLineWidth(0.45)
            canvas.line(p1[0], p1[1], p2[0], p2[1])
            length = round(
                hypot(
                    dimension.end.x_mm - dimension.start.x_mm,
                    dimension.end.y_mm - dimension.start.y_mm,
                )
            )
            label = dimension.label_override or f"{length} mm"
            canvas.drawCentredString((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0 + 2.0, label)

    if config.show_annotations:
        canvas.setFillGray(0.2)
        canvas.setFont("Helvetica", 7)
        for annotation in scene.annotations:
            x, y = transform.point((annotation.anchor.x_mm, annotation.anchor.y_mm))
            canvas.drawString(x, y, annotation.text)

    if config.show_north_arrow:
        anchor_x = page_width - config.margin_mm * mm - 18 * mm
        anchor_y = page_height - config.margin_mm * mm - 18 * mm
        theta = radians(scene.north_rotation_udeg / 1_000_000.0)
        dx = sin(theta) * 12 * mm
        dy = cos(theta) * 12 * mm
        canvas.setStrokeGray(0.05)
        canvas.setFillGray(0.05)
        canvas.setLineWidth(1.2)
        canvas.line(anchor_x, anchor_y, anchor_x + dx, anchor_y + dy)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(anchor_x + dx, anchor_y + dy + 3, "N")

    margin = config.margin_mm * mm
    canvas.setStrokeGray(0.25)
    canvas.setLineWidth(0.6)
    canvas.line(
        margin,
        margin + config.title_block_height_mm * mm,
        page_width - margin,
        margin + config.title_block_height_mm * mm,
    )
    canvas.setFillGray(0.15)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(margin, margin + 8 * mm, scene.floor_name)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(margin, margin + 4.5 * mm, f"Revision: {scene.revision_id}")
    canvas.drawRightString(
        page_width - margin,
        margin + 8 * mm,
        "Plan geometry stored at 1 mm resolution",
    )
    canvas.drawRightString(
        page_width - margin,
        margin + 4.5 * mm,
        f"Plan hash: {scene.source_plan_hash[:16]}",
    )

    canvas.showPage()
    canvas.save()
    assert scene.scene_hash is not None
    filename = f"floor-{scene.floor_index}-{scene.revision_id}.pdf"
    return ExportArtifact.create(
        format="PDF",
        filename=filename,
        media_type="application/pdf",
        content=buffer.getvalue(),
        scene_hash=scene.scene_hash,
    )
