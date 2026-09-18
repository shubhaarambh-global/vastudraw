from __future__ import annotations

import math

from ai_vastu.solver import PlannerBoundarySide

_DIRECTION_BEARINGS: dict[str, float] = {
    "N": 0.0,
    "NE": 45.0,
    "E": 90.0,
    "SE": 135.0,
    "S": 180.0,
    "SW": 225.0,
    "W": 270.0,
    "NW": 315.0,
}
_LOCAL_SIDES: tuple[tuple[PlannerBoundarySide, float], ...] = (
    (PlannerBoundarySide.SOUTH, 180.0),
    (PlannerBoundarySide.EAST, 90.0),
    (PlannerBoundarySide.NORTH, 0.0),
    (PlannerBoundarySide.WEST, 270.0),
)


def _circular_difference(first: float, second: float) -> float:
    raw = abs(first - second) % 360.0
    return min(raw, 360.0 - raw)


def local_boundary_side(
    direction: str,
    *,
    north_rotation_deg: float,
) -> PlannerBoundarySide:
    """Map a verified true-world direction to a rectangular local boundary side."""

    target = _DIRECTION_BEARINGS.get(direction)
    if target is None:
        raise ValueError(f"Unsupported direction: {direction}")

    candidates: list[tuple[float, PlannerBoundarySide]] = []
    for side, local_bearing in _LOCAL_SIDES:
        true_bearing = (local_bearing - north_rotation_deg) % 360.0
        candidates.append((_circular_difference(true_bearing, target), side))

    candidates.sort(key=lambda item: (item[0], item[1].value))
    best_difference = candidates[0][0]
    if best_difference > 22.5 + 1e-9:
        raise ValueError(
            "Direction does not correspond to a rectangular boundary edge "
            "under the confirmed true-North rotation."
        )
    tied = [item for item in candidates if math.isclose(item[0], best_difference, abs_tol=1e-9)]
    if len(tied) != 1:
        raise ValueError("Direction is ambiguous between rectangular boundary edges.")
    return tied[0][1]
