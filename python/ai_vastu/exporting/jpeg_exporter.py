from __future__ import annotations

from io import BytesIO
from math import ceil, cos, hypot, radians, sin

from PIL import Image, ImageDraw, ImageFont

from ai_vastu.plan_schema import IntPolygon

from .dimension_units import format_dimension_length_mm
from .geometry import (
    offset_segment,
    opening_segments,
    polygon_center,
    scene_bounds,
    visible_wall_segments,
)
from .models import DrawingScene, ExportArtifact, RasterExportConfig


class _RasterTransform:
    def __init__(self, scene: DrawingScene, config: RasterExportConfig) -> None:
        bounds = scene_bounds(scene)
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


def _polygon_points(
    polygon: IntPolygon,
    transform: _RasterTransform,
) -> list[tuple[float, float]]:
    return [transform.point((point.x_mm, point.y_mm)) for point in polygon.outer]


def render_jpeg(scene: DrawingScene, config: RasterExportConfig) -> ExportArtifact:
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()
    image = Image.new("RGB", (config.width_px, config.height_px), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    transform = _RasterTransform(scene, config)

    plot_points = _polygon_points(scene.plot_boundary, transform)
    buildable_points = _polygon_points(scene.buildable_boundary, transform)
    floor_points = _polygon_points(scene.floor_boundary, transform)
    draw.line([*plot_points, plot_points[0]], fill=(152, 162, 179), width=2)
    draw.line([*buildable_points, buildable_points[0]], fill=(180, 190, 205), width=2)
    draw.line([*floor_points, floor_points[0]], fill=(52, 64, 84), width=3)

    for room in scene.rooms:
        points = _polygon_points(room.polygon, transform)
        draw.polygon(points, outline=(102, 112, 133))
        if config.show_room_labels:
            center = transform.point(polygon_center(room.polygon))
            label = room.name or room.room_type.value.replace("_", " ").title()
            bbox = draw.textbbox((0, 0), label, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            draw.text(
                (center[0] - width / 2, center[1] - height / 2),
                label,
                fill=(52, 64, 84),
                font=font,
            )

    for furniture in scene.furniture:
        points = _polygon_points(furniture.footprint, transform)
        draw.polygon(points, outline=(152, 162, 179))
    for stair in scene.stairs:
        points = _polygon_points(stair.footprint, transform)
        draw.polygon(points, outline=(71, 84, 103))

    for segment in visible_wall_segments(scene):
        width_px = max(1, ceil(segment.thickness_mm * transform.scale))
        draw.line(
            [transform.point(segment.start), transform.point(segment.end)],
            fill=(24, 34, 48),
            width=width_px,
        )
    for opening in opening_segments(scene):
        draw.line(
            [transform.point(opening.start), transform.point(opening.end)],
            fill=(18, 183, 106),
            width=max(2, ceil(35 * transform.scale)),
        )

    if config.show_dimensions:
        for dimension in scene.dimensions:
            start, end = offset_segment(dimension.start, dimension.end, dimension.offset_mm)
            p1 = transform.point(start)
            p2 = transform.point(end)
            draw.line([p1, p2], fill=(102, 112, 133), width=1)
            length = round(
                hypot(
                    dimension.end.x_mm - dimension.start.x_mm,
                    dimension.end.y_mm - dimension.start.y_mm,
                )
            )
            label = dimension.label_override or format_dimension_length_mm(
                length,
                config.dimension_unit,
            )
            midpoint = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
            draw.text(midpoint, label, fill=(71, 84, 103), font=font, anchor="mm")

    if config.show_annotations:
        for annotation in scene.annotations:
            draw.text(
                transform.point((annotation.anchor.x_mm, annotation.anchor.y_mm)),
                annotation.text,
                fill=(52, 64, 84),
                font=font,
            )

    if config.show_north_arrow:
        x = config.width_px - config.margin_px - 35
        y = config.margin_px + 45
        angle_deg = scene.north_rotation_udeg / 1_000_000.0
        angle = radians(angle_deg)
        dx = sin(angle) * 30
        dy = -cos(angle) * 30
        draw.line([(x, y), (x + dx, y + dy)], fill=(16, 24, 40), width=3)
        draw.text((x + dx, y + dy - 10), "N", fill=(16, 24, 40), font=font, anchor="ms")

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
