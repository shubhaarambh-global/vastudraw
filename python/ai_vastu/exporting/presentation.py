from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, pi, radians, sin
from uuid import UUID

from ai_vastu.plan_schema import (
    DoorHinge,
    DoorSwing,
    IntPolygon,
    Opening,
    OpeningKind,
    RoomGeometry,
    RoomType,
    SiteSpaceKind,
    Wall,
    WallCategory,
)

from .dimension_units import format_dimension_length_mm
from .geometry import axis_length, point_on_axis, polygon_bounds
from .models import DimensionDisplayUnit, DrawingScene


@dataclass(frozen=True, slots=True)
class WorldSegment:
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True, slots=True)
class RoomLabelGraphic:
    room_id: UUID
    title: str
    dimension: str
    center: tuple[float, float]
    non_rectangular: bool


@dataclass(frozen=True, slots=True)
class DoorGraphic:
    opening_id: UUID
    wall_id: UUID
    hinge: tuple[float, float]
    closed_end: tuple[float, float]
    open_end: tuple[float, float]
    swing_arc: tuple[tuple[float, float], ...]
    sliding: bool
    derived_swing: bool


@dataclass(frozen=True, slots=True)
class WindowGraphic:
    opening_id: UUID
    wall_id: UUID
    lines: tuple[WorldSegment, ...]


@dataclass(frozen=True, slots=True)
class PlainOpeningGraphic:
    opening_id: UUID
    wall_id: UUID
    segment: WorldSegment


@dataclass(frozen=True, slots=True)
class StairGraphic:
    stair_id: UUID
    outline: IntPolygon
    treads: tuple[WorldSegment, ...]
    landing: WorldSegment | None
    flight_divider: WorldSegment | None
    arrow: WorldSegment
    direction_label: str


@dataclass(frozen=True, slots=True)
class PresentationSymbol:
    owner_room_id: UUID
    kind: str
    bounds: tuple[float, float, float, float]
    rotation_udeg: int = 0


@dataclass(frozen=True, slots=True)
class DimensionGraphic:
    start: tuple[float, float]
    end: tuple[float, float]
    dimension_start: tuple[float, float]
    dimension_end: tuple[float, float]
    label: str
    category: str


@dataclass(frozen=True, slots=True)
class ProfessionalPresentation:
    room_labels: tuple[RoomLabelGraphic, ...]
    doors: tuple[DoorGraphic, ...]
    windows: tuple[WindowGraphic, ...]
    plain_openings: tuple[PlainOpeningGraphic, ...]
    stairs: tuple[StairGraphic, ...]
    symbols: tuple[PresentationSymbol, ...]
    dimensions: tuple[DimensionGraphic, ...]


_SANITARY_TYPES = frozenset(
    {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
)
_BEDROOM_TYPES = frozenset(
    {
        RoomType.MASTER_BEDROOM,
        RoomType.BEDROOM,
        RoomType.PARENTS_BEDROOM,
        RoomType.GUEST_BEDROOM,
        RoomType.CHILDREN_BEDROOM,
        RoomType.SERVANT_ROOM,
    }
)
_LIVING_TYPES = frozenset({RoomType.LIVING, RoomType.DRAWING, RoomType.FAMILY_LOUNGE})


def _title(value: str) -> str:
    return value.replace("_", " ").upper()


def _is_axis_aligned_rectangle(polygon: IntPolygon) -> bool:
    points = polygon.outer
    if len(points) != 4 or polygon.holes:
        return False
    bounds = polygon_bounds(polygon)
    corners = {
        (bounds.min_x_mm, bounds.min_y_mm),
        (bounds.max_x_mm, bounds.min_y_mm),
        (bounds.max_x_mm, bounds.max_y_mm),
        (bounds.min_x_mm, bounds.max_y_mm),
    }
    return {(float(point.x_mm), float(point.y_mm)) for point in points} == corners


def _room_label(room: RoomGeometry, unit: DimensionDisplayUnit) -> RoomLabelGraphic:
    bounds = polygon_bounds(room.polygon)
    rectangular = _is_axis_aligned_rectangle(room.polygon)
    width = round(bounds.width_mm)
    depth = round(bounds.height_mm)
    prefix = "" if rectangular else "MAX "
    dimension = (
        f"{prefix}{format_dimension_length_mm(width, unit)} x "
        f"{format_dimension_length_mm(depth, unit)}"
    )
    return RoomLabelGraphic(
        room_id=room.id,
        title=_title(room.name or room.room_type.value),
        dimension=dimension,
        center=(
            (bounds.min_x_mm + bounds.max_x_mm) / 2.0,
            (bounds.min_y_mm + bounds.max_y_mm) / 2.0,
        ),
        non_rectangular=not rectangular,
    )


def _wall_room_candidates(wall: Wall, rooms: tuple[RoomGeometry, ...]) -> tuple[RoomGeometry, ...]:
    wall_min_x = min(wall.axis.start.x_mm, wall.axis.end.x_mm)
    wall_max_x = max(wall.axis.start.x_mm, wall.axis.end.x_mm)
    wall_min_y = min(wall.axis.start.y_mm, wall.axis.end.y_mm)
    wall_max_y = max(wall.axis.start.y_mm, wall.axis.end.y_mm)
    result: list[RoomGeometry] = []
    for room in rooms:
        bounds = polygon_bounds(room.polygon)
        if wall_min_x == wall_max_x:
            shared = min(wall_max_y, bounds.max_y_mm) - max(wall_min_y, bounds.min_y_mm)
            touches = wall_min_x in (bounds.min_x_mm, bounds.max_x_mm) and shared > 0
        elif wall_min_y == wall_max_y:
            shared = min(wall_max_x, bounds.max_x_mm) - max(wall_min_x, bounds.min_x_mm)
            touches = wall_min_y in (bounds.min_y_mm, bounds.max_y_mm) and shared > 0
        else:
            touches = False
        if touches:
            result.append(room)
    return tuple(sorted(result, key=lambda item: str(item.id)))


def _door_target_room(wall: Wall, rooms: tuple[RoomGeometry, ...]) -> RoomGeometry | None:
    candidates = _wall_room_candidates(wall, rooms)
    if not candidates:
        return None
    if wall.category is WallCategory.EXTERNAL:
        return candidates[0]
    sanitary = tuple(room for room in candidates if room.room_type in _SANITARY_TYPES)
    return sanitary[0] if sanitary else candidates[0]


def _normal_toward_room(
    wall: Wall,
    room: RoomGeometry | None,
) -> tuple[float, float]:
    length = axis_length(wall.axis)
    tangent = (
        (wall.axis.end.x_mm - wall.axis.start.x_mm) / length,
        (wall.axis.end.y_mm - wall.axis.start.y_mm) / length,
    )
    normal = (-tangent[1], tangent[0])
    if room is None:
        return normal
    bounds = polygon_bounds(room.polygon)
    room_center = (
        (bounds.min_x_mm + bounds.max_x_mm) / 2.0,
        (bounds.min_y_mm + bounds.max_y_mm) / 2.0,
    )
    wall_center = (
        (wall.axis.start.x_mm + wall.axis.end.x_mm) / 2.0,
        (wall.axis.start.y_mm + wall.axis.end.y_mm) / 2.0,
    )
    dot = (room_center[0] - wall_center[0]) * normal[0] + (
        room_center[1] - wall_center[1]
    ) * normal[1]
    return normal if dot >= 0 else (-normal[0], -normal[1])


def _arc_points(
    center: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[tuple[float, float], ...]:
    radius = hypot(start[0] - center[0], start[1] - center[1])
    start_angle = atan2(start[1] - center[1], start[0] - center[0])
    end_angle = atan2(end[1] - center[1], end[0] - center[0])
    delta = (end_angle - start_angle + pi) % (2 * pi) - pi
    steps = 8
    return tuple(
        (
            center[0] + cos(start_angle + delta * index / steps) * radius,
            center[1] + sin(start_angle + delta * index / steps) * radius,
        )
        for index in range(steps + 1)
    )


def _opening_points(
    opening: Opening,
    wall: Wall,
) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        point_on_axis(wall.axis, float(opening.offset_from_wall_start_mm)),
        point_on_axis(
            wall.axis,
            float(opening.offset_from_wall_start_mm + opening.width_mm),
        ),
    )


def _door_graphic(
    opening: Opening,
    wall: Wall,
    rooms: tuple[RoomGeometry, ...],
) -> DoorGraphic:
    start, end = _opening_points(opening, wall)
    hinge_is_start = opening.hinge is not DoorHinge.RIGHT
    hinge = start if hinge_is_start else end
    closed_end = end if hinge_is_start else start
    sliding = opening.swing is DoorSwing.SLIDING
    normal = _normal_toward_room(wall, _door_target_room(wall, rooms))
    if opening.swing is DoorSwing.OUT:
        normal = (-normal[0], -normal[1])
    open_end = (
        hinge[0] + normal[0] * opening.width_mm,
        hinge[1] + normal[1] * opening.width_mm,
    )
    return DoorGraphic(
        opening_id=opening.id,
        wall_id=opening.wall_id,
        hinge=hinge,
        closed_end=closed_end,
        open_end=open_end,
        swing_arc=() if sliding else _arc_points(hinge, closed_end, open_end),
        sliding=sliding,
        derived_swing=opening.hinge is None or opening.swing in (None, DoorSwing.NONE),
    )


def _window_graphic(opening: Opening, wall: Wall) -> WindowGraphic:
    start, end = _opening_points(opening, wall)
    length = hypot(end[0] - start[0], end[1] - start[1])
    normal = (-(end[1] - start[1]) / length, (end[0] - start[0]) / length)
    half = wall.thickness_mm * 0.28
    lines = tuple(
        WorldSegment(
            start=(start[0] + normal[0] * offset, start[1] + normal[1] * offset),
            end=(end[0] + normal[0] * offset, end[1] + normal[1] * offset),
        )
        for offset in (-half, 0.0, half)
    )
    return WindowGraphic(opening_id=opening.id, wall_id=wall.id, lines=lines)


def _stair_graphic(scene: DrawingScene, stair_index: int) -> StairGraphic:
    stair = scene.stairs[stair_index]
    bounds = polygon_bounds(stair.footprint)
    horizontal_run = bounds.width_mm >= bounds.height_mm
    run_min = bounds.min_x_mm if horizontal_run else bounds.min_y_mm
    run_max = bounds.max_x_mm if horizontal_run else bounds.max_y_mm
    cross_min = bounds.min_y_mm if horizontal_run else bounds.min_x_mm
    cross_max = bounds.max_y_mm if horizontal_run else bounds.max_x_mm
    run_length = run_max - run_min
    landing_depth = min(float(stair.landing_depth_mm), run_length * 0.35)
    landing_at = run_min + run_length / 2.0
    usable = max(0.0, run_length - landing_depth)
    tread_count = max(2, min(stair.number_of_risers // 2, int(usable / stair.tread_mm)))
    treads: list[WorldSegment] = []
    if tread_count:
        left_end = landing_at - landing_depth / 2.0
        right_start = landing_at + landing_depth / 2.0
        for index in range(1, tread_count + 1):
            ratio = index / (tread_count + 1)
            for position in (
                run_min + (left_end - run_min) * ratio,
                right_start + (run_max - right_start) * ratio,
            ):
                start = (position, cross_min) if horizontal_run else (cross_min, position)
                end = (position, cross_max) if horizontal_run else (cross_max, position)
                treads.append(WorldSegment(start=start, end=end))
    landing = WorldSegment(
        start=(landing_at, cross_min) if horizontal_run else (cross_min, landing_at),
        end=(landing_at, cross_max) if horizontal_run else (cross_max, landing_at),
    )
    cross_mid = (cross_min + cross_max) / 2.0
    divider = WorldSegment(
        start=(run_min, cross_mid) if horizontal_run else (cross_mid, run_min),
        end=(run_max, cross_mid) if horizontal_run else (cross_mid, run_max),
    )
    center = (
        (bounds.min_x_mm + bounds.max_x_mm) / 2.0,
        (bounds.min_y_mm + bounds.max_y_mm) / 2.0,
    )
    theta = radians(stair.direction_udeg / 1_000_000.0)
    arrow_length = min(bounds.width_mm, bounds.height_mm) * 0.7
    direction = (sin(theta), cos(theta))
    arrow = WorldSegment(
        start=(
            center[0] - direction[0] * arrow_length / 2.0,
            center[1] - direction[1] * arrow_length / 2.0,
        ),
        end=(
            center[0] + direction[0] * arrow_length / 2.0,
            center[1] + direction[1] * arrow_length / 2.0,
        ),
    )
    return StairGraphic(
        stair_id=stair.id,
        outline=stair.footprint,
        treads=tuple(treads),
        landing=landing,
        flight_divider=divider,
        arrow=arrow,
        direction_label="UP",
    )


def _inset_bounds(room: RoomGeometry, inset: float = 220.0) -> tuple[float, float, float, float]:
    bounds = polygon_bounds(room.polygon)
    return (
        bounds.min_x_mm + inset,
        bounds.min_y_mm + inset,
        bounds.max_x_mm - inset,
        bounds.max_y_mm - inset,
    )


def _symbol(room: RoomGeometry) -> PresentationSymbol | None:
    x0, y0, x1, y1 = _inset_bounds(room)
    width = x1 - x0
    depth = y1 - y0
    if width <= 500 or depth <= 500 or room.room_type is RoomType.STAIRCASE:
        return None
    kind: str | None = None
    target_width = width * 0.72
    target_depth = depth * 0.58
    if room.room_type in _BEDROOM_TYPES:
        kind = "bed"
        target_width = min(1_800.0, width * 0.68)
        target_depth = min(2_100.0, depth * 0.7)
    elif room.room_type in _LIVING_TYPES:
        kind = "sofa"
        target_width = min(2_400.0, width * 0.74)
        target_depth = min(850.0, depth * 0.3)
    elif room.room_type is RoomType.DINING:
        kind = "dining"
        target_width = min(1_800.0, width * 0.58)
        target_depth = min(1_000.0, depth * 0.42)
    elif room.room_type in _SANITARY_TYPES:
        kind = "sanitary"
        target_width = min(1_200.0, width * 0.72)
        target_depth = min(1_500.0, depth * 0.68)
    elif room.room_type is RoomType.KITCHEN:
        kind = "kitchen-counter"
        target_width = min(width, max(900.0, width * 0.9))
        target_depth = min(600.0, depth * 0.28)
    elif room.room_type in (RoomType.PARKING, RoomType.GARAGE):
        kind = "vehicle"
        target_width = min(1_800.0, width * 0.72)
        target_depth = min(4_500.0, depth * 0.8)
    elif room.room_type in (RoomType.STUDY, RoomType.HOME_OFFICE):
        kind = "desk"
        target_width = min(1_500.0, width * 0.62)
        target_depth = min(700.0, depth * 0.3)
    if kind is None or target_width < 400 or target_depth < 400:
        return None
    center_x = (x0 + x1) / 2.0
    center_y = (y0 + y1) / 2.0
    if kind == "bed":
        center_x = x0 + target_width / 2.0
        center_y = y1 - target_depth / 2.0
    elif kind in {"sofa", "dining", "sanitary", "kitchen-counter", "desk"}:
        center_x = x0 + target_width / 2.0
        center_y = y0 + target_depth / 2.0
    elif kind == "vehicle":
        center_x = x0 + target_width / 2.0
    return PresentationSymbol(
        owner_room_id=room.id,
        kind=kind,
        bounds=(
            center_x - target_width / 2.0,
            center_y - target_depth / 2.0,
            center_x + target_width / 2.0,
            center_y + target_depth / 2.0,
        ),
    )


def _dimension(
    start: tuple[float, float],
    end: tuple[float, float],
    offset: tuple[float, float],
    unit: DimensionDisplayUnit,
    category: str,
) -> DimensionGraphic:
    length = round(hypot(end[0] - start[0], end[1] - start[1]))
    return DimensionGraphic(
        start=start,
        end=end,
        dimension_start=(start[0] + offset[0], start[1] + offset[1]),
        dimension_end=(end[0] + offset[0], end[1] + offset[1]),
        label=format_dimension_length_mm(length, unit),
        category=category,
    )


def _auto_dimensions(
    scene: DrawingScene,
    unit: DimensionDisplayUnit,
) -> tuple[DimensionGraphic, ...]:
    plot = polygon_bounds(scene.plot_boundary)
    floor = polygon_bounds(scene.floor_boundary)
    result = [
        _dimension(
            (plot.min_x_mm, plot.min_y_mm),
            (plot.max_x_mm, plot.min_y_mm),
            (0.0, -900.0),
            unit,
            "site",
        ),
        _dimension(
            (plot.max_x_mm, plot.min_y_mm),
            (plot.max_x_mm, plot.max_y_mm),
            (900.0, 0.0),
            unit,
            "site",
        ),
    ]
    if floor != plot:
        result.extend(
            (
                _dimension(
                    (floor.min_x_mm, floor.max_y_mm),
                    (floor.max_x_mm, floor.max_y_mm),
                    (0.0, 550.0),
                    unit,
                    "building",
                ),
                _dimension(
                    (floor.min_x_mm, floor.min_y_mm),
                    (floor.min_x_mm, floor.max_y_mm),
                    (-550.0, 0.0),
                    unit,
                    "building",
                ),
            )
        )
    return tuple(result)


def site_space_label(kind: SiteSpaceKind, label: str | None) -> str:
    return (label or kind.value.replace("_", " ")).upper()


def build_professional_presentation(
    scene: DrawingScene,
    *,
    dimension_unit: DimensionDisplayUnit = DimensionDisplayUnit.METRES,
) -> ProfessionalPresentation:
    walls = {wall.id: wall for wall in scene.walls}
    doors: list[DoorGraphic] = []
    windows: list[WindowGraphic] = []
    plain_openings: list[PlainOpeningGraphic] = []
    for opening in scene.openings:
        wall = walls[opening.wall_id]
        if opening.kind is OpeningKind.DOOR:
            doors.append(_door_graphic(opening, wall, scene.rooms))
        elif opening.kind is OpeningKind.WINDOW:
            windows.append(_window_graphic(opening, wall))
        else:
            start, end = _opening_points(opening, wall)
            plain_openings.append(
                PlainOpeningGraphic(
                    opening_id=opening.id,
                    wall_id=wall.id,
                    segment=WorldSegment(start=start, end=end),
                )
            )
    symbols = tuple(symbol for room in scene.rooms if (symbol := _symbol(room)) is not None)
    return ProfessionalPresentation(
        room_labels=tuple(_room_label(room, dimension_unit) for room in scene.rooms),
        doors=tuple(doors),
        windows=tuple(windows),
        plain_openings=tuple(plain_openings),
        stairs=tuple(_stair_graphic(scene, index) for index in range(len(scene.stairs))),
        symbols=symbols,
        dimensions=_auto_dimensions(scene, dimension_unit),
    )
