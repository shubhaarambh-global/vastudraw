from __future__ import annotations

from io import BytesIO
from math import cos, hypot, radians, sin

from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from ai_vastu.plan_schema import IntPoint, RoomType, SiteSpaceKind, WallCategory

from .dimension_units import format_dimension_length_mm
from .geometry import (
    offset_segment,
    padded_scene_bounds,
    polygon_center,
    visible_wall_segments,
)
from .models import DrawingScene, ExportArtifact, PdfExportConfig
from .presentation import build_professional_presentation, site_space_label


class _PdfTransform:
    def __init__(
        self,
        scene: DrawingScene,
        config: PdfExportConfig,
        page_width: float,
        page_height: float,
    ) -> None:
        bounds = padded_scene_bounds(scene)
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
    presentation = build_professional_presentation(
        scene,
        dimension_unit=config.dimension_unit,
    )
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

    site_fill = {
        SiteSpaceKind.LANDSCAPE: (0.94, 0.97, 0.94),
        SiteSpaceKind.VEHICLE_ACCESS: (0.96, 0.95, 0.93),
        SiteSpaceKind.UTILITY_YARD: (0.97, 0.96, 0.92),
        SiteSpaceKind.LIGHTWELL: (0.95, 0.98, 0.98),
        SiteSpaceKind.SHAFT: (0.93, 0.94, 0.94),
        SiteSpaceKind.PORCH: (0.97, 0.95, 0.93),
        SiteSpaceKind.OPEN_SPACE: (0.98, 0.98, 0.97),
    }
    for space in scene.site_spaces:
        red, green, blue = site_fill[space.kind]
        canvas.setFillColorRGB(red, green, blue)
        canvas.setStrokeGray(0.72)
        points = space.polygon.outer
        path = canvas.beginPath()
        first = transform.point((points[0].x_mm, points[0].y_mm))
        path.moveTo(*first)
        for point in points[1:]:
            path.lineTo(*transform.point((point.x_mm, point.y_mm)))
        path.close()
        canvas.drawPath(path, stroke=1, fill=1)
        center = transform.point(polygon_center(space.polygon))
        canvas.setFillGray(0.42)
        canvas.setFont("Helvetica", 5.5)
        canvas.drawCentredString(
            center[0],
            center[1] - 2,
            site_space_label(space.kind, space.label),
        )

    canvas.setStrokeColorRGB(0.86, 0.85, 0.82)
    for road in scene.roads:
        for axis in road.axes:
            start = transform.point((axis.start.x_mm, axis.start.y_mm))
            end = transform.point((axis.end.x_mm, axis.end.y_mm))
            canvas.setLineWidth(max(2.0, (road.width_mm or 900) * transform.scale))
            canvas.line(start[0], start[1], end[0], end[1])

    label_index = {label.room_id: label for label in presentation.room_labels}
    sanitary_types = {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
    for room in scene.rooms:
        if room.room_type is RoomType.KITCHEN:
            canvas.setFillColorRGB(0.98, 0.97, 0.93)
        elif room.room_type in sanitary_types:
            canvas.setFillColorRGB(0.95, 0.98, 0.98)
        else:
            canvas.setFillColorRGB(0.99, 0.99, 0.98)
        canvas.setStrokeGray(0.45)
        points = room.polygon.outer
        path = canvas.beginPath()
        first = transform.point((points[0].x_mm, points[0].y_mm))
        path.moveTo(*first)
        for point in points[1:]:
            path.lineTo(*transform.point((point.x_mm, point.y_mm)))
        path.close()
        canvas.setLineWidth(0.35)
        canvas.drawPath(path, stroke=0, fill=1)
        if config.show_room_labels:
            center = transform.point(polygon_center(room.polygon))
            label = label_index[room.id]
            canvas.setFillGray(0.18)
            canvas.setFont("Helvetica-Bold", 7)
            canvas.drawCentredString(center[0], center[1] + 1, label.title)
            canvas.setFillGray(0.34)
            canvas.setFont("Helvetica", 5.5)
            canvas.drawCentredString(center[0], center[1] - 6, label.dimension)

    canvas.setLineCap(2)
    canvas.setStrokeGray(0.08)
    for segment in visible_wall_segments(scene):
        start = transform.point(segment.start)
        end = transform.point(segment.end)
        canvas.setStrokeGray(0.07 if segment.category is WallCategory.EXTERNAL else 0.22)
        canvas.setLineWidth(max(0.45, segment.thickness_mm * transform.scale))
        canvas.line(start[0], start[1], end[0], end[1])

    canvas.setStrokeGray(0.25)
    for window in presentation.windows:
        for line in window.lines:
            start = transform.point(line.start)
            end = transform.point(line.end)
            canvas.setLineWidth(0.65)
            canvas.line(start[0], start[1], end[0], end[1])
    for opening in presentation.plain_openings:
        start = transform.point(opening.segment.start)
        end = transform.point(opening.segment.end)
        canvas.setLineWidth(0.55)
        canvas.line(start[0], start[1], end[0], end[1])
    for door in presentation.doors:
        hinge = transform.point(door.hinge)
        if door.sliding:
            closed = transform.point(door.closed_end)
            canvas.line(hinge[0], hinge[1], closed[0], closed[1])
            continue
        opened = transform.point(door.open_end)
        canvas.setLineWidth(0.65)
        canvas.line(hinge[0], hinge[1], opened[0], opened[1])
        arc = tuple(transform.point(point) for point in door.swing_arc)
        path = canvas.beginPath()
        path.moveTo(*arc[0])
        for arc_point in arc[1:]:
            path.lineTo(*arc_point)
        canvas.setLineWidth(0.35)
        canvas.drawPath(path, stroke=1, fill=0)

    canvas.setStrokeGray(0.35)
    for stair in presentation.stairs:
        _draw_polygon(canvas, stair.outline.outer, transform, line_width=0.6)
        canvas.setLineWidth(0.3)
        for tread in stair.treads:
            start = transform.point(tread.start)
            end = transform.point(tread.end)
            canvas.line(start[0], start[1], end[0], end[1])
        arrow_start = transform.point(stair.arrow.start)
        arrow_end = transform.point(stair.arrow.end)
        canvas.setStrokeColorRGB(0.12, 0.34, 0.26)
        canvas.setLineWidth(0.75)
        canvas.line(arrow_start[0], arrow_start[1], arrow_end[0], arrow_end[1])
        canvas.setFillColorRGB(0.12, 0.34, 0.26)
        canvas.setFont("Helvetica-Bold", 5.5)
        canvas.drawCentredString(arrow_end[0], arrow_end[1] + 3, stair.direction_label)
    for furniture in scene.furniture:
        _draw_polygon(canvas, furniture.footprint.outer, transform, line_width=0.35)

    if not scene.furniture or not scene.fixtures:
        canvas.setStrokeGray(0.58)
        canvas.setFillGray(0.97)
        for symbol in presentation.symbols:
            if scene.furniture and symbol.kind in {"bed", "sofa", "dining", "desk"}:
                continue
            if scene.fixtures and symbol.kind in {"sanitary", "kitchen-counter"}:
                continue
            x0, y0, x1, y1 = symbol.bounds
            left, bottom = transform.point((x0, y0))
            right, top = transform.point((x1, y1))
            canvas.rect(
                min(left, right),
                min(bottom, top),
                abs(right - left),
                abs(top - bottom),
                stroke=1,
                fill=1,
            )

    if config.show_dimensions:
        canvas.setStrokeGray(0.4)
        canvas.setFillGray(0.3)
        canvas.setFont("Helvetica", 6.5)
        for canonical_dimension in scene.dimensions:
            start, end = offset_segment(
                canonical_dimension.start,
                canonical_dimension.end,
                canonical_dimension.offset_mm,
            )
            p1 = transform.point(start)
            p2 = transform.point(end)
            canvas.setLineWidth(0.45)
            canvas.line(p1[0], p1[1], p2[0], p2[1])
            length = round(
                hypot(
                    canonical_dimension.end.x_mm - canonical_dimension.start.x_mm,
                    canonical_dimension.end.y_mm - canonical_dimension.start.y_mm,
                )
            )
            dimension_text = canonical_dimension.label_override or format_dimension_length_mm(
                length,
                config.dimension_unit,
            )
            canvas.drawCentredString(
                (p1[0] + p2[0]) / 2.0,
                (p1[1] + p2[1]) / 2.0 + 2.0,
                dimension_text,
            )
        for auto_dimension in presentation.dimensions:
            source_start = transform.point(auto_dimension.start)
            source_end = transform.point(auto_dimension.end)
            p1 = transform.point(auto_dimension.dimension_start)
            p2 = transform.point(auto_dimension.dimension_end)
            canvas.line(source_start[0], source_start[1], p1[0], p1[1])
            canvas.line(source_end[0], source_end[1], p2[0], p2[1])
            canvas.line(p1[0], p1[1], p2[0], p2[1])
            canvas.drawCentredString(
                (p1[0] + p2[0]) / 2.0,
                (p1[1] + p2[1]) / 2.0 + 2.0,
                auto_dimension.label,
            )

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
        (
            "Canonical geometry: integer mm · dimensions: "
            + ("feet + inches" if config.dimension_unit.value == "ft-in" else "metres")
        ),
    )
    canvas.drawRightString(
        page_width - margin,
        margin + 4.5 * mm,
        f"Plan hash: {scene.source_plan_hash[:16]}",
    )
    canvas.setFillGray(0.12)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(margin, page_height - margin + 2, "VASTUDRAW")
    scale_start = margin
    scale_end = margin + 5_000 * transform.scale
    scale_y = margin + config.title_block_height_mm * mm + 5 * mm
    canvas.setLineWidth(1.0)
    canvas.line(scale_start, scale_y, scale_end, scale_y)
    canvas.line(scale_start, scale_y - 2, scale_start, scale_y + 2)
    canvas.line(scale_end, scale_y - 2, scale_end, scale_y + 2)
    canvas.setFont("Helvetica", 5.5)
    canvas.drawCentredString((scale_start + scale_end) / 2, scale_y + 3, "5 m")

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
