from __future__ import annotations

from html import escape
from math import cos, radians, sin

from ai_vastu.plan_schema import IntPolygon, RoomType, SiteSpaceKind, WallCategory

from .geometry import padded_scene_bounds, polygon_center, visible_wall_segments
from .models import DrawingScene, ExportArtifact, SvgExportConfig
from .presentation import build_professional_presentation, site_space_label


class _SvgTransform:
    def __init__(self, scene: DrawingScene, config: SvgExportConfig) -> None:
        bounds = padded_scene_bounds(scene)
        usable_width = max(1.0, config.width_px - config.margin_px * 2)
        usable_height = max(1.0, config.height_px - config.margin_px * 2)
        self.scale = min(
            usable_width / max(bounds.width_mm, 1.0),
            usable_height / max(bounds.height_mm, 1.0),
        )
        drawn_width = bounds.width_mm * self.scale
        drawn_height = bounds.height_mm * self.scale
        self.left = config.margin_px + (usable_width - drawn_width) / 2.0
        self.top = config.margin_px + (usable_height - drawn_height) / 2.0
        self.min_x = bounds.min_x_mm
        self.max_y = bounds.max_y_mm

    def point(self, value: tuple[float, float]) -> tuple[float, float]:
        return (
            self.left + (value[0] - self.min_x) * self.scale,
            self.top + (self.max_y - value[1]) * self.scale,
        )


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _point(value: tuple[float, float]) -> str:
    return f"{_number(value[0])},{_number(value[1])}"


def _polygon_points(polygon: IntPolygon, transform: _SvgTransform) -> str:
    return " ".join(
        _point(transform.point((point.x_mm, point.y_mm))) for point in polygon.outer
    )


def _line(
    start: tuple[float, float],
    end: tuple[float, float],
    transform: _SvgTransform,
    *,
    class_name: str,
    stroke_width: float | None = None,
) -> str:
    x1, y1 = transform.point(start)
    x2, y2 = transform.point(end)
    width = "" if stroke_width is None else f' stroke-width="{_number(stroke_width)}"'
    return (
        f'<line class="{class_name}" x1="{_number(x1)}" y1="{_number(y1)}" '
        f'x2="{_number(x2)}" y2="{_number(y2)}"{width}/>'
    )


def _room_fill(room_type: RoomType) -> str:
    if room_type is RoomType.KITCHEN:
        return "#fbf8ee"
    if room_type in {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }:
        return "#f1f7f7"
    if room_type in {RoomType.STAIRCASE, RoomType.PARKING, RoomType.GARAGE}:
        return "#f5f5f1"
    return "#fbfbf8"


def _site_fill(kind: SiteSpaceKind) -> str:
    return {
        SiteSpaceKind.LANDSCAPE: "#eef5ed",
        SiteSpaceKind.VEHICLE_ACCESS: "#f1f0eb",
        SiteSpaceKind.UTILITY_YARD: "#f5f2ea",
        SiteSpaceKind.LIGHTWELL: "#eff5f5",
        SiteSpaceKind.SHAFT: "#eff1f1",
        SiteSpaceKind.PORCH: "#f5f2ea",
        SiteSpaceKind.OPEN_SPACE: "#f7f7f3",
    }[kind]


def render_svg(scene: DrawingScene, config: SvgExportConfig) -> ExportArtifact:
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()
    transform = _SvgTransform(scene, config)
    presentation = build_professional_presentation(
        scene,
        dimension_unit=config.dimension_unit,
    )
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{config.width_px}" '
            f'height="{config.height_px}" viewBox="0 0 {config.width_px} {config.height_px}" '
            f'role="img" aria-labelledby="title description" '
            f'data-source-plan-hash="{scene.source_plan_hash}" '
            f'data-floor-index="{scene.floor_index}">'
        ),
        f"<title id=\"title\">Vastudraw {escape(scene.floor_name)} architectural plan</title>",
        (
            "<desc id=\"description\">Professional vector presentation derived from "
            "canonical PlanDocument geometry.</desc>"
        ),
        """<defs>
<marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
<path d="M0,0 L0,6 L7,3 z" fill="#236049"/>
</marker>
<style>
.site-boundary{fill:#fff;stroke:#5d6661;stroke-width:1.5}
.buildable{fill:none;stroke:#aab2ad;stroke-width:1;stroke-dasharray:5 4}
.floor{fill:none;stroke:#303733;stroke-width:1.5}
.site-space{stroke:#b9c0bb;stroke-width:.8}
.road{stroke:#e3e1dc;stroke-linecap:butt}
.wall{stroke:#3d4641;stroke-linecap:square}
.wall-external{stroke:#171d1a}
.window{stroke:#375e66;stroke-width:1.35}
.door{stroke:#29322d;stroke-width:1.35;fill:none}
.door-swing{stroke:#8a948e;stroke-width:.8;stroke-dasharray:2 1;fill:none}
.stair{fill:#f7f7f3;stroke:#3e4842;stroke-width:1.15}
.stair-detail{stroke:#8b948f;stroke-width:.75}
.stair-arrow{stroke:#236049;stroke-width:1.5}
.symbol{fill:#f8f8f4;stroke:#939c97;stroke-width:.85}
.label{fill:#28312d;font:700 11px sans-serif;text-anchor:middle;paint-order:stroke;
stroke:#fcfcf9;stroke-width:3}
.sub-label{fill:#69756f;font:9px sans-serif}
.annotation{fill:#59635d;font:9px sans-serif}
.dimension{stroke:#747e78;stroke-width:.7;fill:none}
.dimension-text{fill:#59635d;font:9px sans-serif;text-anchor:middle;paint-order:stroke;
stroke:#fcfcf9;stroke-width:2}
.sheet{fill:#24312b;font:800 13px sans-serif;letter-spacing:1px}
.sheet-sub{fill:#64716b;font:10px sans-serif}
.north{stroke:#1a5f49;fill:#1a5f49;stroke-width:1.6}
.scale{stroke:#29322e;stroke-width:2}
.site-label{fill:#7b867f;font:8px sans-serif;text-anchor:middle}
</style>
</defs>""",
        '<g id="site-background">',
    ]
    for road in scene.roads:
        for axis in road.axes:
            parts.append(
                _line(
                    (axis.start.x_mm, axis.start.y_mm),
                    (axis.end.x_mm, axis.end.y_mm),
                    transform,
                    class_name="road",
                    stroke_width=max(2.0, (road.width_mm or 900) * transform.scale),
                )
            )
    parts.append(
        '<polygon class="site-boundary" '
        f'points="{_polygon_points(scene.plot_boundary, transform)}"/>'
    )
    for space in scene.site_spaces:
        center = transform.point(polygon_center(space.polygon))
        site_label_text = escape(site_space_label(space.kind, space.label))
        parts.append(
            f'<g data-site-kind="{space.kind.value}"><polygon class="site-space" '
            f'fill="{_site_fill(space.kind)}" '
            f'points="{_polygon_points(space.polygon, transform)}"/>'
            f'<text class="site-label" x="{_number(center[0])}" '
            f'y="{_number(center[1])}">{site_label_text}</text></g>'
        )
    parts.extend(
        [
            '<polygon class="buildable" '
            f'points="{_polygon_points(scene.buildable_boundary, transform)}"/>',
            f'<polygon class="floor" points="{_polygon_points(scene.floor_boundary, transform)}"/>',
            "</g>",
            '<g id="room-fills">',
        ]
    )
    for room in scene.rooms:
        parts.append(
            f'<polygon data-room-id="{room.id}" fill="{_room_fill(room.room_type)}" '
            f'points="{_polygon_points(room.polygon, transform)}"/>'
        )
    parts.append("</g>")

    parts.append('<g id="presentation-objects">')
    for furniture in scene.furniture:
        parts.append(
            f'<polygon class="symbol" data-kind="{escape(furniture.furniture_type)}" '
            f'points="{_polygon_points(furniture.footprint, transform)}"/>'
        )
    for fixture in scene.fixtures:
        if fixture.footprint is not None:
            parts.append(
                f'<polygon class="symbol" data-kind="{escape(fixture.fixture_type)}" '
                f'points="{_polygon_points(fixture.footprint, transform)}"/>'
            )
    if not scene.furniture or not scene.fixtures:
        for symbol in presentation.symbols:
            if scene.furniture and symbol.kind in {"bed", "sofa", "dining", "desk"}:
                continue
            if scene.fixtures and symbol.kind in {"sanitary", "kitchen-counter"}:
                continue
            x0, y0 = transform.point((symbol.bounds[0], symbol.bounds[3]))
            x1, y1 = transform.point((symbol.bounds[2], symbol.bounds[1]))
            parts.append(
                f'<rect class="symbol" data-kind="{escape(symbol.kind)}" '
                f'data-owner-room-id="{symbol.owner_room_id}" x="{_number(min(x0, x1))}" '
                f'y="{_number(min(y0, y1))}" width="{_number(abs(x1 - x0))}" '
                f'height="{_number(abs(y1 - y0))}" rx="3"/>'
            )
    parts.append("</g>")

    parts.append('<g id="stairs">')
    for stair in presentation.stairs:
        parts.append(
            f'<g data-stair-id="{stair.stair_id}"><polygon class="stair" '
            f'points="{_polygon_points(stair.outline, transform)}"/>'
        )
        for tread in stair.treads:
            parts.append(
                _line(
                    tread.start,
                    tread.end,
                    transform,
                    class_name="stair-detail",
                )
            )
        if stair.landing is not None:
            parts.append(
                _line(
                    stair.landing.start,
                    stair.landing.end,
                    transform,
                    class_name="stair-detail",
                )
            )
        if stair.flight_divider is not None:
            parts.append(
                _line(
                    stair.flight_divider.start,
                    stair.flight_divider.end,
                    transform,
                    class_name="stair-detail",
                )
            )
        arrow = _line(
            stair.arrow.start,
            stair.arrow.end,
            transform,
            class_name="stair-arrow",
        ).replace("/>", ' marker-end="url(#arrow)"/>')
        arrow_end = transform.point(stair.arrow.end)
        parts.extend(
            [
                arrow,
                f'<text class="annotation" x="{_number(arrow_end[0])}" '
                f'y="{_number(arrow_end[1] - 7)}" text-anchor="middle">UP</text></g>',
            ]
        )
    parts.append("</g>")

    parts.append('<g id="walls">')
    for wall in visible_wall_segments(scene):
        category = (
            "wall-external" if wall.category is WallCategory.EXTERNAL else "wall-interior"
        )
        parts.append(
            _line(
                wall.start,
                wall.end,
                transform,
                class_name=f"wall {category}",
                stroke_width=max(1.0, wall.thickness_mm * transform.scale),
            )
        )
    parts.append("</g>")

    parts.append('<g id="openings">')
    for window in presentation.windows:
        parts.append(f'<g class="window" data-opening-id="{window.opening_id}">')
        for line in window.lines:
            parts.append(_line(line.start, line.end, transform, class_name="window"))
        parts.append("</g>")
    for opening in presentation.plain_openings:
        plain_line = _line(
            opening.segment.start,
            opening.segment.end,
            transform,
            class_name="window",
        )
        parts.append(
            f'<g class="plain-opening" '
            f'data-opening-id="{opening.opening_id}">{plain_line}</g>'
        )
    for door in presentation.doors:
        end = door.closed_end if door.sliding else door.open_end
        parts.append(f'<g class="door" data-opening-id="{door.opening_id}">')
        parts.append(_line(door.hinge, end, transform, class_name="door"))
        if door.swing_arc:
            arc = " ".join(_point(transform.point(point)) for point in door.swing_arc)
            parts.append(f'<polyline class="door-swing" points="{arc}"/>')
        parts.append("</g>")
    parts.append("</g>")

    if config.show_room_labels:
        parts.append('<g id="room-labels">')
        for room_label in presentation.room_labels:
            x, y = transform.point(room_label.center)
            parts.append(
                f'<text class="label" x="{_number(x)}" y="{_number(y - 3)}">'
                f'{escape(room_label.title)}<tspan class="sub-label" '
                f'x="{_number(x)}" dy="13">'
                f"{escape(room_label.dimension)}</tspan></text>"
            )
        parts.append("</g>")

    if config.show_dimensions:
        parts.append('<g id="dimensions">')
        for dimension in presentation.dimensions:
            parts.extend(
                [
                    _line(
                        dimension.start,
                        dimension.dimension_start,
                        transform,
                        class_name="dimension",
                    ),
                    _line(
                        dimension.end,
                        dimension.dimension_end,
                        transform,
                        class_name="dimension",
                    ),
                    _line(
                        dimension.dimension_start,
                        dimension.dimension_end,
                        transform,
                        class_name="dimension",
                    ),
                ]
            )
            start = transform.point(dimension.dimension_start)
            end = transform.point(dimension.dimension_end)
            parts.append(
                f'<text class="dimension-text" x="{_number((start[0] + end[0]) / 2)}" '
                f'y="{_number((start[1] + end[1]) / 2 - 5)}">'
                f"{escape(dimension.label)}</text>"
            )
        parts.append("</g>")

    if config.show_annotations:
        parts.append('<g id="annotations">')
        for annotation in scene.annotations:
            x, y = transform.point((annotation.anchor.x_mm, annotation.anchor.y_mm))
            parts.append(
                f'<text class="annotation" x="{_number(x)}" y="{_number(y)}">'
                f"{escape(annotation.text)}</text>"
            )
        parts.append("</g>")

    parts.append('<g id="sheet-annotations">')
    parts.append('<text class="sheet" x="28" y="30">VASTUDRAW</text>')
    parts.append(
        f'<text class="sheet-sub" x="28" y="47">{escape(scene.floor_name.upper())}</text>'
    )
    if config.show_north_arrow:
        anchor = (config.width_px - 65.0, 72.0)
        theta = radians(scene.north_rotation_udeg / 1_000_000.0)
        north_end = (anchor[0] + sin(theta) * 36, anchor[1] - cos(theta) * 36)
        parts.append(
            f'<line class="north" x1="{_number(anchor[0])}" y1="{_number(anchor[1])}" '
            f'x2="{_number(north_end[0])}" y2="{_number(north_end[1])}" '
            'marker-end="url(#arrow)"/>'
        )
        parts.append(
            f'<text class="sheet" x="{_number(north_end[0])}" '
            f'y="{_number(north_end[1] - 8)}" text-anchor="middle">N</text>'
        )
    scale_start = (config.margin_px, config.height_px - 28.0)
    scale_end = (scale_start[0] + 5_000 * transform.scale, scale_start[1])
    parts.extend(
        [
            f'<line class="scale" x1="{_number(scale_start[0])}" y1="{_number(scale_start[1])}" '
            f'x2="{_number(scale_end[0])}" y2="{_number(scale_end[1])}"/>',
            f'<text class="sheet-sub" x="{_number((scale_start[0] + scale_end[0]) / 2)}" '
            f'y="{_number(scale_start[1] - 7)}" text-anchor="middle">5 m</text>',
            "</g>",
            "</svg>",
        ]
    )
    content = "\n".join(parts).encode("utf-8")
    assert scene.scene_hash is not None
    return ExportArtifact.create(
        format="SVG",
        filename=f"floor-{scene.floor_index}-{scene.revision_id}.svg",
        media_type="image/svg+xml",
        content=content,
        scene_hash=scene.scene_hash,
    )
