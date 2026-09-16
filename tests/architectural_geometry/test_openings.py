from __future__ import annotations

import pytest

from ai_vastu.architectural_geometry import (
    OpeningBuildRequest,
    OpeningPlacementError,
    build_architectural_geometry,
)
from ai_vastu.plan_schema import DoorHinge, DoorSwing, OpeningKind

from .helpers import build_request


def test_explicit_opening_attaches_to_deterministic_wall() -> None:
    base = build_request()
    first = build_architectural_geometry(base)
    wall = next(item for item in first.floor.walls if _length(item) >= 1200)
    request = base.model_copy(
        update={
            "openings": (
                OpeningBuildRequest(
                    wall_id=wall.id,
                    kind=OpeningKind.DOOR,
                    offset_from_wall_start_mm=100,
                    width_mm=900,
                    height_mm=2100,
                    hinge=DoorHinge.LEFT,
                    swing=DoorSwing.IN,
                ),
            )
        }
    )
    built = build_architectural_geometry(request)
    assert len(built.floor.openings) == 1
    opening = built.floor.openings[0]
    assert opening.wall_id == wall.id
    assert opening.offset_from_wall_start_mm == 100
    assert opening.width_mm == 900


def test_opening_beyond_wall_fails_closed() -> None:
    base = build_request()
    first = build_architectural_geometry(base)
    wall = first.floor.walls[0]
    request = base.model_copy(
        update={
            "openings": (
                OpeningBuildRequest(
                    wall_id=wall.id,
                    kind=OpeningKind.WINDOW,
                    offset_from_wall_start_mm=_length(wall),
                    width_mm=600,
                    height_mm=1200,
                    sill_height_mm=900,
                ),
            )
        }
    )
    with pytest.raises(OpeningPlacementError, match="extends beyond"):
        build_architectural_geometry(request)


def _length(wall: object) -> int:
    axis = wall.axis  # type: ignore[attr-defined]
    return abs(axis.end.x_mm - axis.start.x_mm) + abs(axis.end.y_mm - axis.start.y_mm)
