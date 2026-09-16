from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, pi, sin
from uuid import UUID

from ai_vastu.plan_schema import AxisSegment, IntPoint, IntPolygon, Opening, Wall, WallCategory

from .errors import ExportSceneError
from .models import DrawingScene


@dataclass(frozen=True, slots=True)
class SceneBounds:
    min_x_mm: float
    min_y_mm: float
    max_x_mm: float
    max_y_mm: float

    @property
    def width_mm(self) -> float:
        return self.max_x_mm - self.min_x_mm

    @property
    def height_mm(self) -> float:
        return self.max_y_mm - self.min_y_mm


@dataclass(frozen=True, slots=True)
class WallStrokeSegment:
    wall_id: UUID
    category: WallCategory
    thickness_mm: int
    start: tuple[float, float]
    end: tuple[float, float]


@dataclass(frozen=True, slots=True)
class OpeningStrokeSegment:
    opening_id: UUID
    wall_id: UUID
    start: tuple[float, float]
    end: tuple[float, float]


def polygon_bounds(polygon: IntPolygon) -> SceneBounds:
    points = polygon.outer
    return SceneBounds(
        min_x_mm=float(min(point.x_mm for point in points)),
        min_y_mm=float(min(point.y_mm for point in points)),
        max_x_mm=float(max(point.x_mm for point in points)),
        max_y_mm=float(max(point.y_mm for point in points)),
    )


def scene_bounds(scene: DrawingScene) -> SceneBounds:
    candidates = [
        polygon_bounds(scene.plot_boundary),
        polygon_bounds(scene.buildable_boundary),
        polygon_bounds(scene.floor_boundary),
    ]
    return SceneBounds(
        min_x_mm=min(item.min_x_mm for item in candidates),
        min_y_mm=min(item.min_y_mm for item in candidates),
        max_x_mm=max(item.max_x_mm for item in candidates),
        max_y_mm=max(item.max_y_mm for item in candidates),
    )


def polygon_center(polygon: IntPolygon) -> tuple[float, float]:
    bounds = polygon_bounds(polygon)
    return (
        (bounds.min_x_mm + bounds.max_x_mm) / 2.0,
        (bounds.min_y_mm + bounds.max_y_mm) / 2.0,
    )


def axis_length(axis: AxisSegment) -> float:
    return hypot(axis.end.x_mm - axis.start.x_mm, axis.end.y_mm - axis.start.y_mm)


def point_on_axis(axis: AxisSegment, distance_mm: float) -> tuple[float, float]:
    length = axis_length(axis)
    if length <= 0:
        raise ExportSceneError("Cannot export a zero-length wall axis.")
    if distance_mm < 0 or distance_mm > length + 1e-7:
        raise ExportSceneError("Opening offset lies outside its wall axis.")
    ratio = distance_mm / length
    return (
        axis.start.x_mm + (axis.end.x_mm - axis.start.x_mm) * ratio,
        axis.start.y_mm + (axis.end.y_mm - axis.start.y_mm) * ratio,
    )


def _openings_by_wall(scene: DrawingScene) -> dict[UUID, list[Opening]]:
    result: dict[UUID, list[Opening]] = {}
    for opening in scene.openings:
        result.setdefault(opening.wall_id, []).append(opening)
    for values in result.values():
        values.sort(key=lambda item: (item.offset_from_wall_start_mm, str(item.id)))
    return result


def visible_wall_segments(scene: DrawingScene) -> tuple[WallStrokeSegment, ...]:
    openings_by_wall = _openings_by_wall(scene)
    result: list[WallStrokeSegment] = []
    for wall in scene.walls:
        length = axis_length(wall.axis)
        cursor = 0.0
        for opening in openings_by_wall.get(wall.id, []):
            start_offset = float(opening.offset_from_wall_start_mm)
            end_offset = start_offset + float(opening.width_mm)
            if end_offset > length + 1e-7:
                raise ExportSceneError("Opening extends beyond wall during export.")
            if start_offset < cursor - 1e-7:
                raise ExportSceneError("Overlapping openings encountered during export.")
            if start_offset > cursor:
                result.append(
                    WallStrokeSegment(
                        wall_id=wall.id,
                        category=wall.category,
                        thickness_mm=wall.thickness_mm,
                        start=point_on_axis(wall.axis, cursor),
                        end=point_on_axis(wall.axis, start_offset),
                    )
                )
            cursor = end_offset
        if cursor < length:
            result.append(
                WallStrokeSegment(
                    wall_id=wall.id,
                    category=wall.category,
                    thickness_mm=wall.thickness_mm,
                    start=point_on_axis(wall.axis, cursor),
                    end=point_on_axis(wall.axis, length),
                )
            )
    return tuple(result)


def opening_segments(scene: DrawingScene) -> tuple[OpeningStrokeSegment, ...]:
    walls: dict[UUID, Wall] = {wall.id: wall for wall in scene.walls}
    result: list[OpeningStrokeSegment] = []
    for opening in scene.openings:
        wall = walls.get(opening.wall_id)
        if wall is None:
            raise ExportSceneError("Opening references an unknown wall during export.")
        start_offset = float(opening.offset_from_wall_start_mm)
        end_offset = start_offset + float(opening.width_mm)
        result.append(
            OpeningStrokeSegment(
                opening_id=opening.id,
                wall_id=opening.wall_id,
                start=point_on_axis(wall.axis, start_offset),
                end=point_on_axis(wall.axis, end_offset),
            )
        )
    return tuple(result)


def offset_segment(
    start: IntPoint,
    end: IntPoint,
    offset_mm: int,
) -> tuple[tuple[float, float], tuple[float, float]]:
    dx = end.x_mm - start.x_mm
    dy = end.y_mm - start.y_mm
    length = hypot(dx, dy)
    if length <= 0:
        raise ExportSceneError("Cannot export a zero-length dimension.")
    nx = -dy / length
    ny = dx / length
    return (
        (start.x_mm + nx * offset_mm, start.y_mm + ny * offset_mm),
        (end.x_mm + nx * offset_mm, end.y_mm + ny * offset_mm),
    )


def north_vector(north_rotation_udeg: int, length_mm: float) -> tuple[float, float]:
    radians = (north_rotation_udeg / 1_000_000.0) * pi / 180.0
    return (sin(radians) * length_mm, cos(radians) * length_mm)
