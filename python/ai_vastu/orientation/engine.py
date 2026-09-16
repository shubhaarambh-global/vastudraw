from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from math import atan2, degrees
from uuid import UUID

from ai_vastu.plan_schema import (
    IntPoint,
    Orientation,
    OrientationSource,
    Plot,
    Road,
    quantize_angle_udeg,
)
from ai_vastu.plan_schema.units import FULL_TURN_UDEG, MICRODEGREES_PER_DEGREE
from ai_vastu.plot import get_plot_edge, signed_double_area

from .errors import AmbiguousRoadFacingError, OrientationError


class Direction8(StrEnum):
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"


_DIRECTION8_ORDER = (
    Direction8.N,
    Direction8.NE,
    Direction8.E,
    Direction8.SE,
    Direction8.S,
    Direction8.SW,
    Direction8.W,
    Direction8.NW,
)
SECTOR_UDEG = 45 * MICRODEGREES_PER_DEGREE
HALF_SECTOR_UDEG = SECTOR_UDEG // 2


@dataclass(frozen=True, slots=True)
class EdgeDirectionAnalysis:
    edge_id: UUID
    edge_index: int
    tangent_drawing_bearing_udeg: int
    tangent_true_bearing_udeg: int
    outward_drawing_bearing_udeg: int
    outward_true_bearing_udeg: int
    outward_direction_8: Direction8


@dataclass(frozen=True, slots=True)
class RoadFacingAnalysis:
    road_id: UUID
    edge_analyses: tuple[EdgeDirectionAnalysis, ...]
    uniform_direction_8: Direction8 | None


def create_orientation(
    *,
    north_rotation_degrees: Decimal | int | str,
    source: OrientationSource = OrientationSource.USER,
    verified: bool = False,
) -> Orientation:
    """Create true-North orientation from clockwise degrees relative to drawing +Y."""

    quantized = quantize_angle_udeg(north_rotation_degrees)
    return Orientation(
        north_rotation_udeg=quantized.microdegrees,
        source=source,
        verified=verified,
    )


def orientation_from_drawing_north(
    direction: Direction8,
    *,
    source: OrientationSource = OrientationSource.USER,
    verified: bool = False,
) -> Orientation:
    index = _DIRECTION8_ORDER.index(direction)
    return Orientation(
        north_rotation_udeg=index * SECTOR_UDEG,
        source=source,
        verified=verified,
    )


def classify_direction8(true_bearing_udeg: int) -> Direction8:
    normalized = true_bearing_udeg % FULL_TURN_UDEG
    index = ((normalized + HALF_SECTOR_UDEG) // SECTOR_UDEG) % len(_DIRECTION8_ORDER)
    return _DIRECTION8_ORDER[index]


def true_bearing_udeg(drawing_bearing_udeg: int, orientation: Orientation) -> int:
    """Convert a drawing bearing to clockwise true bearing from true North."""

    return (drawing_bearing_udeg - orientation.north_rotation_udeg) % FULL_TURN_UDEG


def drawing_bearing_udeg(start: IntPoint, end: IntPoint) -> int:
    """Clockwise bearing from drawing +Y, quantized to one microdegree.

    This is derived analysis, never canonical positional geometry. Axis-aligned vectors
    use exact constants; non-axis vectors use atan2 and deterministic decimal rounding.
    """

    dx = end.x_mm - start.x_mm
    dy = end.y_mm - start.y_mm
    if dx == 0 and dy == 0:
        raise OrientationError("Cannot derive a bearing from a zero-length vector.")
    if dx == 0:
        return 0 if dy > 0 else 180 * MICRODEGREES_PER_DEGREE
    if dy == 0:
        return 90 * MICRODEGREES_PER_DEGREE if dx > 0 else 270 * MICRODEGREES_PER_DEGREE

    clockwise_degrees = degrees(atan2(dx, dy)) % 360.0
    decimal_degrees = Decimal(str(clockwise_degrees))
    return quantize_angle_udeg(decimal_degrees).microdegrees


def edge_direction_analysis(
    plot: Plot, edge_id: UUID, orientation: Orientation
) -> EdgeDirectionAnalysis:
    edge = get_plot_edge(plot, edge_id)
    signed_area = signed_double_area(plot.boundary.outer)
    if signed_area == 0:
        raise OrientationError("Cannot determine outward normal of a zero-area plot.")

    tangent_drawing = drawing_bearing_udeg(edge.start, edge.end)
    # CCW boundary: interior is left of the edge, so outward is the right normal.
    outward_delta = (
        90 * MICRODEGREES_PER_DEGREE
        if signed_area > 0
        else -90 * MICRODEGREES_PER_DEGREE
    )
    outward_drawing = (tangent_drawing + outward_delta) % FULL_TURN_UDEG
    tangent_true = true_bearing_udeg(tangent_drawing, orientation)
    outward_true = true_bearing_udeg(outward_drawing, orientation)
    return EdgeDirectionAnalysis(
        edge_id=edge.id,
        edge_index=edge.index,
        tangent_drawing_bearing_udeg=tangent_drawing,
        tangent_true_bearing_udeg=tangent_true,
        outward_drawing_bearing_udeg=outward_drawing,
        outward_true_bearing_udeg=outward_true,
        outward_direction_8=classify_direction8(outward_true),
    )


def analyze_road_facing(plot: Plot, road: Road, orientation: Orientation) -> RoadFacingAnalysis:
    if not road.plot_edge_ids:
        raise OrientationError("Road must reference at least one plot edge before facing analysis.")
    analyses = tuple(
        edge_direction_analysis(plot, edge_id, orientation) for edge_id in road.plot_edge_ids
    )
    directions = {analysis.outward_direction_8 for analysis in analyses}
    uniform = next(iter(directions)) if len(directions) == 1 else None
    return RoadFacingAnalysis(
        road_id=road.id,
        edge_analyses=analyses,
        uniform_direction_8=uniform,
    )


def require_uniform_road_facing_direction(
    plot: Plot, road: Road, orientation: Orientation
) -> Direction8:
    analysis = analyze_road_facing(plot, road, orientation)
    if analysis.uniform_direction_8 is None:
        raise AmbiguousRoadFacingError(
            "Road spans plot edges with different outward directions; "
            "no single facing may be inferred."
        )
    return analysis.uniform_direction_8
