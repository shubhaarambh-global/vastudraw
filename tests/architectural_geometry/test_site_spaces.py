from uuid import UUID

from ai_vastu.architectural_geometry import (
    derive_purposeful_site_spaces,
)
from ai_vastu.plan_schema import (
    RoomGeometry,
    RoomType,
    SiteSpaceKind,
)
from ai_vastu.solver.models import (
    PlannerBoundarySide,
)
from tests.exporting.helpers import rectangle

FLOOR_ID = UUID("10000000-0000-0000-0000-000000000001")


def _room(
    number: int,
    room_type: RoomType,
    *,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
) -> RoomGeometry:
    return RoomGeometry(
        id=UUID(f"20000000-0000-0000-0000-{number:012d}"),
        requirement_id=UUID(f"30000000-0000-0000-0000-{number:012d}"),
        room_type=room_type,
        polygon=rectangle(
            x0,
            y0,
            x1,
            y1,
        ),
    )


def test_boundary_rectangle_becomes_open_space() -> None:
    spaces = derive_purposeful_site_spaces(
        floor_id=FLOOR_ID,
        envelope=rectangle(
            0,
            0,
            10_000,
            8_000,
        ),
        rooms=(
            _room(
                1,
                RoomType.LIVING,
                x0=0,
                y0=0,
                x1=8_000,
                y1=8_000,
            ),
        ),
        road_boundary_side=None,
        solver_step_mm=10,
    )

    assert len(spaces) == 1
    assert spaces[0].kind is SiteSpaceKind.OPEN_SPACE


def test_service_adjacent_boundary_strip_becomes_utility_yard() -> None:
    spaces = derive_purposeful_site_spaces(
        floor_id=FLOOR_ID,
        envelope=rectangle(
            0,
            0,
            10_000,
            8_000,
        ),
        rooms=(
            _room(
                1,
                RoomType.KITCHEN,
                x0=0,
                y0=0,
                x1=9_000,
                y1=8_000,
            ),
        ),
        road_boundary_side=None,
        solver_step_mm=10,
    )

    assert len(spaces) == 1
    assert spaces[0].kind is SiteSpaceKind.UTILITY_YARD


def test_compact_internal_rectangle_becomes_lightwell() -> None:
    rooms = (
        _room(
            1,
            RoomType.LIVING,
            x0=0,
            y0=0,
            x1=4_000,
            y1=8_000,
        ),
        _room(
            2,
            RoomType.BEDROOM,
            x0=6_000,
            y0=0,
            x1=10_000,
            y1=8_000,
        ),
        _room(
            3,
            RoomType.LIVING,
            x0=4_000,
            y0=0,
            x1=6_000,
            y1=3_000,
        ),
        _room(
            4,
            RoomType.BEDROOM,
            x0=4_000,
            y0=5_000,
            x1=6_000,
            y1=8_000,
        ),
    )

    spaces = derive_purposeful_site_spaces(
        floor_id=FLOOR_ID,
        envelope=rectangle(
            0,
            0,
            10_000,
            8_000,
        ),
        rooms=rooms,
        road_boundary_side=None,
        solver_step_mm=10,
    )

    assert len(spaces) == 1
    assert spaces[0].kind is SiteSpaceKind.LIGHTWELL


def test_road_to_parking_rectangle_becomes_vehicle_access() -> None:
    rooms = (
        _room(
            1,
            RoomType.PARKING,
            x0=0,
            y0=3_000,
            x1=3_000,
            y1=6_000,
        ),
        _room(
            2,
            RoomType.LIVING,
            x0=3_000,
            y0=0,
            x1=10_000,
            y1=8_000,
        ),
        _room(
            3,
            RoomType.BEDROOM,
            x0=0,
            y0=6_000,
            x1=3_000,
            y1=8_000,
        ),
    )

    spaces = derive_purposeful_site_spaces(
        floor_id=FLOOR_ID,
        envelope=rectangle(
            0,
            0,
            10_000,
            8_000,
        ),
        rooms=rooms,
        road_boundary_side=(PlannerBoundarySide.SOUTH),
        solver_step_mm=10,
    )

    assert len(spaces) == 1
    assert spaces[0].kind is SiteSpaceKind.VEHICLE_ACCESS


def test_direct_road_parking_does_not_invent_vehicle_access() -> None:
    rooms = (
        _room(
            1,
            RoomType.PARKING,
            x0=0,
            y0=0,
            x1=3_000,
            y1=5_500,
        ),
        _room(
            2,
            RoomType.LIVING,
            x0=3_000,
            y0=0,
            x1=10_000,
            y1=8_000,
        ),
        _room(
            3,
            RoomType.BEDROOM,
            x0=0,
            y0=5_500,
            x1=3_000,
            y1=8_000,
        ),
    )

    spaces = derive_purposeful_site_spaces(
        floor_id=FLOOR_ID,
        envelope=rectangle(
            0,
            0,
            10_000,
            8_000,
        ),
        rooms=rooms,
        road_boundary_side=(PlannerBoundarySide.SOUTH),
        solver_step_mm=10,
    )

    assert all(space.kind is not SiteSpaceKind.VEHICLE_ACCESS for space in spaces)


def test_irregular_residual_is_not_disguised_as_open_space() -> None:
    spaces = derive_purposeful_site_spaces(
        floor_id=FLOOR_ID,
        envelope=rectangle(
            0,
            0,
            10_000,
            8_000,
        ),
        rooms=(
            _room(
                1,
                RoomType.LIVING,
                x0=0,
                y0=0,
                x1=8_000,
                y1=6_000,
            ),
        ),
        road_boundary_side=None,
        solver_step_mm=10,
    )

    # Residual is an L-shaped region. It must remain unexplained
    # for Architectural Brain to reject rather than silently
    # calling it useful open space.
    assert spaces == ()
