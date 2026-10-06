from uuid import UUID

import pytest

from ai_vastu.architectural_brain.site_accounting import (
    analyze_floor_site_accounting,
    require_geometric_site_accounting_closed,
)
from ai_vastu.geometry import measure_site_partition
from ai_vastu.plan_schema import (
    AxisSegment,
    Floor,
    IntPoint,
    IntPolygon,
    RoomGeometry,
    RoomType,
    Wall,
    WallCategory,
)


def _rect(x0: int, y0: int, x1: int, y1: int) -> IntPolygon:
    return IntPolygon(
        outer=tuple(
            IntPoint(x_mm=x, y_mm=y)
            for x, y in (
                (x0, y0),
                (x1, y0),
                (x1, y1),
                (x0, y1),
            )
        )
    )


def _wall(number: int, x0: int, y0: int, x1: int, y1: int, thickness: int = 115) -> Wall:
    return Wall(
        id=UUID(int=number),
        axis=AxisSegment(
            start=IntPoint(x_mm=x0, y_mm=y0),
            end=IntPoint(x_mm=x1, y_mm=y1),
        ),
        thickness_mm=thickness,
        height_mm=3000,
        category=WallCategory.INTERNAL,
    )


def _slit(width: int, with_walls: bool = True) -> tuple[IntPolygon, Floor]:
    # Sanitized geometry from the observed 70 x 2030 mm canonical residual.
    envelope = _rect(3000, 3550, 3400, 5580)
    rooms = (
        RoomGeometry(
            id=UUID(int=1), room_type=RoomType.BEDROOM, polygon=_rect(3000, 3550, 3160, 5580)
        ),
        RoomGeometry(
            id=UUID(int=2), room_type=RoomType.LIVING, polygon=_rect(3160 + width, 3550, 3400, 5580)
        ),
    )
    walls = (
        (_wall(3, 3160, 3550, 3160, 5580), _wall(4, 3160 + width, 3550, 3160 + width, 5580))
        if with_walls
        else ()
    )
    floor = Floor(
        id=UUID(int=100),
        index=0,
        name="Ground",
        elevation_mm=0,
        floor_to_floor_mm=3000,
        boundary=envelope,
        rooms=rooms,
        walls=walls,
    )
    return envelope, floor


def test_observed_70mm_canonical_slit_is_actual_wall_material() -> None:
    envelope, floor = _slit(70)
    original = floor.model_dump_json()
    baseline = measure_site_partition(envelope, tuple(room.polygon for room in floor.rooms))
    assert sum(region.area_mm2 for region in baseline.residual_regions) == 142100
    analysis = analyze_floor_site_accounting(envelope=envelope, floor=floor, solver_step_mm=10)
    assert analysis.accounting.residual_area_mm2 == 0
    assert analysis.residual_regions == ()
    assert analysis.numerical_tolerance_mm2 == 10000
    wall = next(item for item in analysis.accounting.allocations if item.category == "WALL")
    assert wall.area_mm2 == 142100
    require_geometric_site_accounting_closed(analysis)
    assert floor.model_dump_json() == original


@pytest.mark.parametrize("width,with_walls,residual", [(70, False, 142100), (230, True, 233450)])
def test_missing_wall_or_wider_gap_remains_unexplained(
    width: int,
    with_walls: bool,
    residual: int,
) -> None:
    envelope, floor = _slit(width, with_walls)
    analysis = analyze_floor_site_accounting(envelope=envelope, floor=floor, solver_step_mm=10)
    assert analysis.accounting.residual_area_mm2 == residual
    assert analysis.unexplained_residual_area_mm2 == residual - 10000
    with pytest.raises(ValueError, match="Unexplained geometric site residual"):
        require_geometric_site_accounting_closed(analysis)


def test_wall_intersections_and_duplicates_are_counted_once() -> None:
    envelope = _rect(0, 0, 1000, 1000)
    horizontal = _wall(1, 0, 500, 1000, 500, 100)
    vertical = _wall(2, 500, 0, 500, 1000, 100)
    measured = measure_site_partition(envelope, (), walls=(horizontal, vertical, horizontal))
    assert measured.wall_material_area_mm2 == 190000
    assert measured.classified_union_area_mm2 == 190000
    assert sum(region.area_mm2 for region in measured.residual_regions) == 810000


def test_exterior_wall_is_clipped_and_ends_are_flat() -> None:
    envelope = _rect(0, 0, 1000, 1000)
    measured = measure_site_partition(envelope, (), walls=(_wall(1, 0, 200, 0, 800, 230),))
    assert measured.wall_material_area_mm2 == 115 * 600
    assert measured.classified_union_area_mm2 == 115 * 600
    outside = measure_site_partition(envelope, (), walls=(_wall(2, -300, 200, -300, 800, 230),))
    assert outside.wall_material_area_mm2 == 0


def test_wall_material_inside_room_is_not_counted_again() -> None:
    envelope = _rect(0, 0, 1000, 1000)
    measured = measure_site_partition(envelope, (envelope,), walls=(_wall(1, 500, 0, 500, 1000),))
    assert measured.wall_material_area_mm2 == 0
    assert measured.classified_union_area_mm2 == 1000000


def test_half_mm_wall_rounding_conserves_integer_partition_area() -> None:
    envelope = _rect(0, 0, 1000, 1000)
    room = RoomGeometry(id=UUID(int=1), room_type=RoomType.LIVING, polygon=_rect(0, 0, 101, 101))
    floor = Floor(
        id=UUID(int=100),
        index=0,
        name="Ground",
        elevation_mm=0,
        floor_to_floor_mm=3000,
        boundary=envelope,
        rooms=(room,),
        walls=(_wall(2, 101, 0, 101, 101, 115),),
    )
    measured = measure_site_partition(envelope, (room.polygon,), walls=floor.walls)
    assert measured.classified_union_area_mm2 == 16008
    assert measured.classified_item_areas_mm2 == (10201,)
    assert measured.wall_material_area_mm2 == 5807
    analysis = analyze_floor_site_accounting(envelope=envelope, floor=floor, solver_step_mm=10)
    accounting = analysis.accounting
    assert sum(item.area_mm2 for item in accounting.allocations) == 16008
    assert accounting.classified_area_mm2 + accounting.residual_area_mm2 == 1000000


def test_overlapping_room_polygons_still_fail_with_walls() -> None:
    envelope, floor = _slit(70)
    room = floor.rooms[0].model_copy(update={"polygon": _rect(3000, 3550, 3400, 5580)})
    floor = floor.model_copy(update={"rooms": (room, floor.rooms[1])})
    with pytest.raises(ValueError, match="overlap"):
        analyze_floor_site_accounting(envelope=envelope, floor=floor, solver_step_mm=10)
