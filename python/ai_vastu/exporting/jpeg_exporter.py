from __future__ import annotations

from io import BytesIO
from math import ceil, cos, hypot, radians, sin

from PIL import Image, ImageDraw, ImageFont

from ai_vastu.plan_schema import IntPolygon, RoomType, SiteSpaceKind, WallCategory

from .dimension_units import format_dimension_length_mm
from .geometry import offset_segment, padded_scene_bounds, visible_wall_segments
from .models import DrawingScene, ExportArtifact, RasterExportConfig
from .presentation import (
    DimensionGraphic,
    PresentationSymbol,
    build_professional_presentation,
    site_space_label,
)


class _RasterTransform:
    """The single canonical-mm to raster-pixel transform for this adapter."""

    def __init__(self, scene: DrawingScene, config: RasterExportConfig) -> None:
        bounds = padded_scene_bounds(scene)
        usable_width = max(1, config.width_px - 2 * config.margin_px)
        usable_height = max(1, config.height_px - 2 * config.margin_px)
        world_width = max(bounds.width_mm, 1.0)
        world_height = max(bounds.height_mm, 1.0)
        self.scale = min(usable_width / world_width, usable_height / world_height)
        drawn_width = world_width * self.scale
        drawn_height = world_height * self.scale
        self.left = config.margin_px + (usable_width - drawn_width) / 2.0
        self.top = config.margin_px + (usable_height - drawn_height) / 2.0
        self.min_x = bounds.min_x_mm
        self.max_y = bounds.max_y_mm

    def point(self, value: tuple[float, float]) -> tuple[float, float]:
        x_mm, y_mm = value
        return (
            self.left + (x_mm - self.min_x) * self.scale,
            self.top + (self.max_y - y_mm) * self.scale,
        )


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size=size)
    except OSError:
        return ImageFont.load_default()


def _polygon_points(
    polygon: IntPolygon,
    transform: _RasterTransform,
) -> list[tuple[float, float]]:
    return [transform.point((point.x_mm, point.y_mm)) for point in polygon.outer]


def _draw_symbol(
    draw: ImageDraw.ImageDraw,
    symbol: PresentationSymbol,
    transform: _RasterTransform,
) -> None:
    x0, y0, x1, y1 = symbol.bounds
    left, bottom = transform.point((x0, y0))
    right, top = transform.point((x1, y1))
    box = (min(left, right), min(top, bottom), max(left, right), max(top, bottom))
    ink = (139, 148, 143)
    pale = (246, 247, 244)
    if symbol.kind == "vehicle":
        draw.rounded_rectangle(
            box,
            radius=max(3, int(180 * transform.scale)),
            fill=pale,
            outline=ink,
            width=2,
        )
        wheel = max(2, int(90 * transform.scale))
        draw.line([(box[0], box[1] + wheel), (box[2], box[1] + wheel)], fill=ink, width=1)
        draw.line([(box[0], box[3] - wheel), (box[2], box[3] - wheel)], fill=ink, width=1)
    elif symbol.kind == "bed":
        draw.rectangle(box, fill=pale, outline=ink, width=2)
        pillow_y = box[1] + (box[3] - box[1]) * 0.22
        draw.line([(box[0], pillow_y), (box[2], pillow_y)], fill=ink, width=1)
        mid = (box[0] + box[2]) / 2
        draw.line([(mid, box[1]), (mid, pillow_y)], fill=ink, width=1)
    elif symbol.kind == "sofa":
        draw.rounded_rectangle(box, radius=4, fill=pale, outline=ink, width=2)
        inset = max(2, int(120 * transform.scale))
        draw.rectangle(
            (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset),
            outline=ink,
        )
    elif symbol.kind == "dining":
        draw.rounded_rectangle(box, radius=3, fill=pale, outline=ink, width=2)
        radius = max(2, int(90 * transform.scale))
        for cx, cy in (
            ((box[0] + box[2]) / 2, box[1] - radius),
            ((box[0] + box[2]) / 2, box[3] + radius),
            (box[0] - radius, (box[1] + box[3]) / 2),
            (box[2] + radius, (box[1] + box[3]) / 2),
        ):
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=ink)
    elif symbol.kind == "sanitary":
        split = box[0] + (box[2] - box[0]) * 0.55
        draw.ellipse((box[0], box[1], split, box[3]), fill=pale, outline=ink, width=2)
        draw.rectangle(
            (split + 2, box[1], box[2], box[1] + (box[3] - box[1]) * 0.42),
            outline=ink,
        )
        draw.ellipse(
            (split + 4, box[1] + 2, box[2] - 2, box[1] + (box[3] - box[1]) * 0.38),
            outline=ink,
        )
    elif symbol.kind == "kitchen-counter":
        draw.rectangle(box, fill=pale, outline=ink, width=2)
        sink_left = box[0] + (box[2] - box[0]) * 0.42
        sink_right = box[0] + (box[2] - box[0]) * 0.68
        draw.rounded_rectangle(
            (sink_left, box[1] + 2, sink_right, box[3] - 2),
            radius=2,
            outline=ink,
        )
        draw.ellipse(
            (box[0] + 4, box[1] + 4, box[0] + 11, box[1] + 11),
            outline=ink,
        )
    else:
        draw.rectangle(box, fill=pale, outline=ink, width=2)


def _draw_dimension(
    draw: ImageDraw.ImageDraw,
    dimension: DimensionGraphic,
    transform: _RasterTransform,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    source_start = transform.point(dimension.start)
    source_end = transform.point(dimension.end)
    start = transform.point(dimension.dimension_start)
    end = transform.point(dimension.dimension_end)
    ink = (93, 101, 96)
    draw.line([source_start, start], fill=ink, width=1)
    draw.line([source_end, end], fill=ink, width=1)
    draw.line([start, end], fill=ink, width=1)
    tick = 5
    for px, py in (start, end):
        draw.line([(px - tick, py + tick), (px + tick, py - tick)], fill=ink, width=1)
    midpoint = ((start[0] + end[0]) / 2.0, (start[1] + end[1]) / 2.0)
    draw.text(
        midpoint,
        dimension.label,
        fill=ink,
        font=font,
        anchor="mm",
        stroke_width=3,
        stroke_fill=(255, 255, 255),
    )


def render_jpeg(scene: DrawingScene, config: RasterExportConfig) -> ExportArtifact:
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()
    image = Image.new("RGB", (config.width_px, config.height_px), (252, 252, 249))
    draw = ImageDraw.Draw(image)
    small_font = _font(15)
    label_font = _font(17, bold=True)
    title_font = _font(22, bold=True)
    transform = _RasterTransform(scene, config)
    presentation = build_professional_presentation(scene, dimension_unit=config.dimension_unit)

    plot_points = _polygon_points(scene.plot_boundary, transform)
    buildable_points = _polygon_points(scene.buildable_boundary, transform)
    floor_points = _polygon_points(scene.floor_boundary, transform)
    draw.polygon(plot_points, fill=(255, 255, 255), outline=(91, 98, 94), width=2)

    site_palette = {
        SiteSpaceKind.LANDSCAPE: (239, 246, 239),
        SiteSpaceKind.VEHICLE_ACCESS: (243, 242, 238),
        SiteSpaceKind.UTILITY_YARD: (244, 243, 236),
        SiteSpaceKind.LIGHTWELL: (242, 247, 247),
        SiteSpaceKind.SHAFT: (237, 239, 239),
        SiteSpaceKind.PORCH: (247, 244, 239),
        SiteSpaceKind.OPEN_SPACE: (248, 248, 245),
    }
    for space in scene.site_spaces:
        points = _polygon_points(space.polygon, transform)
        draw.polygon(points, fill=site_palette[space.kind], outline=(188, 194, 189), width=1)
        center_x = sum(point[0] for point in points) / len(points)
        center_y = sum(point[1] for point in points) / len(points)
        draw.text(
            (center_x, center_y),
            site_space_label(space.kind, space.label),
            fill=(112, 122, 115),
            font=small_font,
            anchor="mm",
        )

    for road in scene.roads:
        for axis in road.axes:
            width_px = max(3, ceil((road.width_mm or 900) * transform.scale))
            draw.line(
                [
                    transform.point((axis.start.x_mm, axis.start.y_mm)),
                    transform.point((axis.end.x_mm, axis.end.y_mm)),
                ],
                fill=(221, 220, 215),
                width=width_px,
            )

    draw.line([*buildable_points, buildable_points[0]], fill=(169, 176, 171), width=1)
    draw.line([*floor_points, floor_points[0]], fill=(40, 44, 42), width=2)

    sanitary_types = {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
    for room in scene.rooms:
        points = _polygon_points(room.polygon, transform)
        fill = (252, 252, 249)
        if room.room_type is RoomType.KITCHEN:
            fill = (250, 248, 239)
        elif room.room_type in sanitary_types:
            fill = (242, 247, 247)
        elif room.room_type in {RoomType.PARKING, RoomType.GARAGE, RoomType.STAIRCASE}:
            fill = (247, 247, 244)
        draw.polygon(points, fill=fill)

    suppress_furniture = bool(scene.furniture)
    suppress_fixtures = bool(scene.fixtures)
    for symbol in presentation.symbols:
        if suppress_furniture and symbol.kind in {"bed", "sofa", "dining", "desk"}:
            continue
        if suppress_fixtures and symbol.kind in {"sanitary", "kitchen-counter"}:
            continue
        _draw_symbol(draw, symbol, transform)
    for furniture in scene.furniture:
        draw.polygon(
            _polygon_points(furniture.footprint, transform),
            outline=(128, 139, 133),
            width=2,
        )
    for fixture in scene.fixtures:
        if fixture.footprint is not None:
            draw.polygon(
                _polygon_points(fixture.footprint, transform),
                outline=(128, 139, 133),
                width=2,
            )
        elif fixture.anchor is not None:
            x, y = transform.point((fixture.anchor.x_mm, fixture.anchor.y_mm))
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(128, 139, 133), width=2)

    for stair in presentation.stairs:
        points = _polygon_points(stair.outline, transform)
        draw.line([*points, points[0]], fill=(58, 64, 60), width=2)
        for tread in stair.treads:
            draw.line(
                [transform.point(tread.start), transform.point(tread.end)],
                fill=(112, 120, 115),
                width=1,
            )
        if stair.landing is not None:
            draw.line(
                [transform.point(stair.landing.start), transform.point(stair.landing.end)],
                fill=(58, 64, 60),
                width=2,
            )
        if stair.flight_divider is not None:
            draw.line(
                [
                    transform.point(stair.flight_divider.start),
                    transform.point(stair.flight_divider.end),
                ],
                fill=(128, 136, 131),
                width=1,
            )
        arrow_start = transform.point(stair.arrow.start)
        arrow_end = transform.point(stair.arrow.end)
        draw.line([arrow_start, arrow_end], fill=(38, 92, 72), width=3)
        draw.polygon(
            [
                arrow_end,
                (arrow_end[0] - 6, arrow_end[1] + 10),
                (arrow_end[0] + 6, arrow_end[1] + 10),
            ],
            fill=(38, 92, 72),
        )
        draw.text(
            arrow_end,
            stair.direction_label,
            fill=(38, 92, 72),
            font=small_font,
            anchor="ms",
        )

    for segment in visible_wall_segments(scene):
        width_px = max(2, ceil(segment.thickness_mm * transform.scale))
        ink = (27, 31, 29) if segment.category is WallCategory.EXTERNAL else (62, 68, 64)
        draw.line(
            [transform.point(segment.start), transform.point(segment.end)],
            fill=ink,
            width=width_px,
        )

    for window in presentation.windows:
        for line in window.lines:
            draw.line(
                [transform.point(line.start), transform.point(line.end)],
                fill=(45, 83, 90),
                width=2,
            )
    for opening in presentation.plain_openings:
        draw.line(
            [transform.point(opening.segment.start), transform.point(opening.segment.end)],
            fill=(105, 111, 107),
            width=2,
        )
    for door in presentation.doors:
        if door.sliding:
            draw.line(
                [transform.point(door.hinge), transform.point(door.closed_end)],
                fill=(59, 66, 62),
                width=2,
            )
            continue
        draw.line(
            [transform.point(door.hinge), transform.point(door.open_end)],
            fill=(43, 49, 46),
            width=2,
        )
        draw.line(
            [transform.point(point) for point in door.swing_arc],
            fill=(114, 121, 117),
            width=1,
        )

    if config.show_room_labels:
        for label in presentation.room_labels:
            center = transform.point(label.center)
            draw.text(
                (center[0], center[1] - 8),
                label.title,
                fill=(36, 43, 39),
                font=label_font,
                anchor="mm",
                stroke_width=3,
                stroke_fill=(252, 252, 249),
            )
            draw.text(
                (center[0], center[1] + 13),
                label.dimension,
                fill=(79, 88, 83),
                font=small_font,
                anchor="mm",
                stroke_width=3,
                stroke_fill=(252, 252, 249),
            )

    if config.show_dimensions:
        for auto_dimension in presentation.dimensions:
            _draw_dimension(draw, auto_dimension, transform, small_font)
        for canonical_dimension in scene.dimensions:
            start, end = offset_segment(
                canonical_dimension.start,
                canonical_dimension.end,
                canonical_dimension.offset_mm,
            )
            p1 = transform.point(start)
            p2 = transform.point(end)
            draw.line([p1, p2], fill=(93, 101, 96), width=1)
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
            draw.text(
                ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0),
                dimension_text,
                fill=(71, 84, 103),
                font=small_font,
                anchor="mm",
                stroke_width=3,
                stroke_fill=(255, 255, 255),
            )

    if config.show_annotations:
        for annotation in scene.annotations:
            draw.text(
                transform.point((annotation.anchor.x_mm, annotation.anchor.y_mm)),
                annotation.text,
                fill=(52, 64, 84),
                font=small_font,
            )

    if config.show_north_arrow:
        x = config.width_px - config.margin_px - 45
        y = config.margin_px + 62
        angle = radians(scene.north_rotation_udeg / 1_000_000.0)
        dx = sin(angle) * 38
        dy = -cos(angle) * 38
        draw.line([(x, y), (x + dx, y + dy)], fill=(24, 73, 57), width=3)
        draw.polygon(
            [
                (x + dx, y + dy),
                (x + dx - 5, y + dy + 11),
                (x + dx + 5, y + dy + 11),
            ],
            fill=(24, 73, 57),
        )
        draw.text(
            (x + dx, y + dy - 12),
            "N",
            fill=(24, 73, 57),
            font=title_font,
            anchor="ms",
        )

    scale_length_mm = 5_000
    scale_px = scale_length_mm * transform.scale
    scale_x = config.margin_px
    scale_y = config.height_px - config.margin_px + 12
    draw.line(
        [(scale_x, scale_y), (scale_x + scale_px, scale_y)],
        fill=(35, 41, 38),
        width=3,
    )
    draw.line([(scale_x, scale_y - 5), (scale_x, scale_y + 5)], fill=(35, 41, 38), width=2)
    draw.line(
        [(scale_x + scale_px, scale_y - 5), (scale_x + scale_px, scale_y + 5)],
        fill=(35, 41, 38),
        width=2,
    )
    draw.text(
        (scale_x + scale_px / 2, scale_y - 8),
        "5 m",
        fill=(35, 41, 38),
        font=small_font,
        anchor="ms",
    )
    draw.text(
        (config.margin_px, config.margin_px - 22),
        f"VASTUDRAW  ·  {scene.floor_name.upper()}",
        fill=(29, 36, 32),
        font=title_font,
    )

    buffer = BytesIO()
    image.save(
        buffer,
        format="JPEG",
        quality=config.jpeg_quality,
        subsampling=0,
        optimize=False,
        progressive=False,
        dpi=(96, 96),
    )
    assert scene.scene_hash is not None
    filename = f"floor-{scene.floor_index}-{scene.revision_id}.jpg"
    return ExportArtifact.create(
        format="JPEG",
        filename=filename,
        media_type="image/jpeg",
        content=buffer.getvalue(),
        scene_hash=scene.scene_hash,
    )
