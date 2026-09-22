from uuid import UUID

from ai_vastu.architectural_geometry import analyze_room_access_graph, validate_circulation
from ai_vastu.plan_schema import (
    AxisSegment,
    Floor,
    IntPoint,
    IntPolygon,
    Opening,
    OpeningKind,
    RoomGeometry,
    RoomType,
    Wall,
    WallCategory,
)


def _room(number: int, room_type: RoomType, x0: int, y0: int, x1: int, y1: int) -> RoomGeometry:
    return RoomGeometry(
        id=UUID(int=number),
        room_type=room_type,
        polygon=IntPolygon(
            outer=(
                IntPoint(x_mm=x0, y_mm=y0),
                IntPoint(x_mm=x1, y_mm=y0),
                IntPoint(x_mm=x1, y_mm=y1),
                IntPoint(x_mm=x0, y_mm=y1),
            )
        ),
    )


def _wall(number: int, x0: int, y0: int, x1: int, y1: int, category: WallCategory) -> Wall:
    return Wall(
        id=UUID(int=100 + number),
        axis=AxisSegment(
            start=IntPoint(x_mm=x0, y_mm=y0),
            end=IntPoint(x_mm=x1, y_mm=y1),
        ),
        thickness_mm=115,
        height_mm=3_000,
        category=category,
    )


def _door(number: int, wall: Wall, width: int = 800) -> Opening:
    return Opening(
        id=UUID(int=200 + number),
        wall_id=wall.id,
        kind=OpeningKind.DOOR,
        offset_from_wall_start_mm=100,
        width_mm=width,
        height_mm=2_100,
    )


def _floor(
    rooms: tuple[RoomGeometry, ...],
    walls: tuple[Wall, ...],
    openings: tuple[Opening, ...],
) -> Floor:
    return Floor(
        id=UUID(int=1),
        index=0,
        name="Ground",
        elevation_mm=0,
        floor_to_floor_mm=3_000,
        rooms=rooms,
        walls=walls,
        openings=openings,
    )


def test_living_kitchen_and_bedrooms_are_reachable_from_entry() -> None:
    living = _room(1, RoomType.LIVING, 0, 0, 4_000, 4_000)
    kitchen = _room(2, RoomType.KITCHEN, 4_000, 0, 8_000, 4_000)
    bedroom = _room(3, RoomType.BEDROOM, 0, 4_000, 4_000, 8_000)
    entry = _wall(1, 0, 0, 4_000, 0, WallCategory.EXTERNAL)
    living_kitchen = _wall(2, 4_000, 0, 4_000, 4_000, WallCategory.INTERNAL)
    living_bedroom = _wall(3, 0, 4_000, 4_000, 4_000, WallCategory.INTERNAL)
    result = validate_circulation(
        _floor(
            (living, kitchen, bedroom),
            (entry, living_kitchen, living_bedroom),
            (_door(1, entry, 900), _door(2, living_kitchen), _door(3, living_bedroom)),
        )
    )
    assert result.accepted


def test_sanitary_room_cannot_be_a_transit_node() -> None:
    living = _room(1, RoomType.LIVING, 0, 0, 4_000, 4_000)
    toilet = _room(2, RoomType.COMMON_TOILET, 4_000, 0, 5_500, 4_000)
    bedroom = _room(3, RoomType.BEDROOM, 5_500, 0, 9_500, 4_000)
    entry = _wall(1, 0, 0, 4_000, 0, WallCategory.EXTERNAL)
    living_toilet = _wall(2, 4_000, 0, 4_000, 4_000, WallCategory.INTERNAL)
    toilet_bedroom = _wall(3, 5_500, 0, 5_500, 4_000, WallCategory.INTERNAL)
    result = validate_circulation(
        _floor(
            (living, toilet, bedroom),
            (entry, living_toilet, toilet_bedroom),
            (_door(1, entry, 900), _door(2, living_toilet), _door(3, toilet_bedroom)),
        )
    )
    assert not result.accepted
    assert result.reason_code == "CIRCULATION_DISCONNECTED"


def test_corner_touching_does_not_create_connectivity() -> None:
    living = _room(1, RoomType.LIVING, 0, 0, 4_000, 4_000)
    kitchen = _room(2, RoomType.KITCHEN, 4_000, 4_000, 8_000, 8_000)
    entry = _wall(1, 0, 0, 4_000, 0, WallCategory.EXTERNAL)
    result = validate_circulation(
        _floor((living, kitchen), (entry,), (_door(1, entry, 900),))
    )
    assert not result.accepted
    assert result.reason_code == "CIRCULATION_DISCONNECTED"


def test_insufficient_shared_wall_does_not_support_a_door() -> None:
    living = _room(1, RoomType.LIVING, 0, 0, 4_000, 4_000)
    kitchen = _room(2, RoomType.KITCHEN, 4_000, 3_500, 4_500, 4_000)
    entry = _wall(1, 0, 0, 4_000, 0, WallCategory.EXTERNAL)
    short_wall = _wall(2, 4_000, 3_500, 4_000, 4_000, WallCategory.INTERNAL)
    result = validate_circulation(
        _floor((living, kitchen), (entry, short_wall), (_door(1, entry, 900), _door(2, short_wall)))
    )
    assert not result.accepted
    assert result.reason_code == "CIRCULATION_DISCONNECTED"


def test_lobby_can_connect_multiple_rooms() -> None:
    living = _room(1, RoomType.LIVING, 0, 0, 4_000, 4_000)
    lobby = _room(2, RoomType.LOBBY, 4_000, 0, 8_000, 4_000)
    kitchen = _room(3, RoomType.KITCHEN, 8_000, 0, 12_000, 4_000)
    bedroom = _room(4, RoomType.BEDROOM, 4_000, 4_000, 8_000, 8_000)
    entry = _wall(1, 0, 0, 4_000, 0, WallCategory.EXTERNAL)
    living_lobby = _wall(2, 4_000, 0, 4_000, 4_000, WallCategory.INTERNAL)
    lobby_kitchen = _wall(3, 8_000, 0, 8_000, 4_000, WallCategory.INTERNAL)
    lobby_bedroom = _wall(4, 4_000, 4_000, 8_000, 4_000, WallCategory.INTERNAL)
    result = validate_circulation(
        _floor(
            (living, lobby, kitchen, bedroom),
            (entry, living_lobby, lobby_kitchen, lobby_bedroom),
            (
                _door(1, entry, 900),
                _door(2, living_lobby),
                _door(3, lobby_kitchen),
                _door(4, lobby_bedroom),
            ),
        )
    )
    assert result.accepted


def test_multiple_floors_keep_independent_graphs() -> None:
    living = _room(1, RoomType.LIVING, 0, 0, 4_000, 4_000)
    kitchen = _room(2, RoomType.KITCHEN, 4_000, 0, 8_000, 4_000)
    entry = _wall(1, 0, 0, 4_000, 0, WallCategory.EXTERNAL)
    shared = _wall(2, 4_000, 0, 4_000, 4_000, WallCategory.INTERNAL)
    connected = _floor((living, kitchen), (entry, shared), (_door(1, entry, 900), _door(2, shared)))
    disconnected = _floor((living, kitchen), (entry,), (_door(1, entry, 900),))
    assert validate_circulation(connected).accepted
    assert not validate_circulation(disconnected).accepted

def test_networkx_access_analysis_reports_articulation_and_sanitary_leaf() -> None:
    living_id = UUID(int=1)
    lobby_id = UUID(int=2)
    bedroom_id = UUID(int=3)
    toilet_id = UUID(int=4)

    analysis = analyze_room_access_graph(
        room_ids=(living_id, lobby_id, bedroom_id, toilet_id),
        edges=(
            (living_id, lobby_id),
            (lobby_id, bedroom_id),
            (lobby_id, toilet_id),
        ),
        root_room_ids=(living_id,),
        required_room_ids=(living_id, lobby_id, bedroom_id, toilet_id),
        sanitary_room_ids=(toilet_id,),
    )

    assert analysis.disconnected_room_ids == ()
    assert analysis.reachable_room_ids == (living_id, lobby_id, bedroom_id, toilet_id)
    assert analysis.connected_components == ((living_id, lobby_id, bedroom_id),)
    assert analysis.articulation_room_ids == (lobby_id,)


def test_networkx_access_analysis_does_not_use_sanitary_room_as_bridge() -> None:
    living_id = UUID(int=1)
    toilet_id = UUID(int=2)
    bedroom_id = UUID(int=3)

    analysis = analyze_room_access_graph(
        room_ids=(living_id, toilet_id, bedroom_id),
        edges=((living_id, toilet_id), (toilet_id, bedroom_id)),
        root_room_ids=(living_id,),
        required_room_ids=(living_id, toilet_id, bedroom_id),
        sanitary_room_ids=(toilet_id,),
    )

    assert analysis.reachable_room_ids == (living_id, toilet_id)
    assert analysis.disconnected_room_ids == (bedroom_id,)
    assert analysis.connected_components == ((living_id,), (bedroom_id,))
