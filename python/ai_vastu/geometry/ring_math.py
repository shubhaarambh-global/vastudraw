from __future__ import annotations

from collections.abc import Iterable, Sequence

from ai_vastu.plan_schema import IntPoint, IntPolygon


def signed_area2_ring(ring: Sequence[IntPoint]) -> int:
    """Return twice the signed area in square millimetres, exactly.

    Positive means counter-clockwise in the canonical +X right/+Y up coordinate frame.
    Twice-area is used because integer-mm vertices can enclose half-square-millimetre areas.
    """
    total = 0
    for index, point in enumerate(ring):
        nxt = ring[(index + 1) % len(ring)]
        total += point.x_mm * nxt.y_mm - nxt.x_mm * point.y_mm
    return total


def area2_polygon(polygon: IntPolygon) -> int:
    outer = abs(signed_area2_ring(polygon.outer))
    holes = sum(abs(signed_area2_ring(hole)) for hole in polygon.holes)
    return outer - holes


def orient_ring(ring: Sequence[IntPoint], *, ccw: bool) -> tuple[IntPoint, ...]:
    is_ccw = signed_area2_ring(ring) > 0
    if is_ccw == ccw:
        return tuple(ring)
    return tuple(reversed(ring))


def canonicalize_polygon(polygon: IntPolygon) -> IntPolygon:
    return IntPolygon(
        outer=orient_ring(polygon.outer, ccw=True),
        holes=tuple(orient_ring(hole, ccw=False) for hole in polygon.holes),
    )


def point_in_ring(point: IntPoint, ring: Sequence[IntPoint]) -> bool:
    """Exact integer ray-casting test. Boundary counts as inside."""
    x, y = point.x_mm, point.y_mm
    inside = False
    for i, a in enumerate(ring):
        b = ring[(i + 1) % len(ring)]
        ax, ay, bx, by = a.x_mm, a.y_mm, b.x_mm, b.y_mm
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if cross == 0 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y):
            # Compare x < ax + (y-ay)*(bx-ax)/(by-ay) without floats.
            lhs = (x - ax) * (by - ay)
            rhs = (y - ay) * (bx - ax)
            intersects = lhs < rhs if (by - ay) > 0 else lhs > rhs
            if intersects:
                inside = not inside
    return inside


def polygon_sort_key(
    polygon: IntPolygon,
) -> tuple[int, int, int, int, int, tuple[tuple[int, int], ...]]:
    xs = [p.x_mm for p in polygon.outer]
    ys = [p.y_mm for p in polygon.outer]
    coords = tuple((p.x_mm, p.y_mm) for p in polygon.outer)
    return (min(xs), min(ys), max(xs), max(ys), -area2_polygon(polygon), coords)


def total_area2(polygons: Iterable[IntPolygon]) -> int:
    return sum(area2_polygon(polygon) for polygon in polygons)
