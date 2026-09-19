from uuid import UUID

import pytest

from ai_vastu.architectural_brain.site_accounting import (
    analyze_floor_site_accounting,
    require_geometric_site_accounting_closed,
)
from ai_vastu.plan_schema import (
    Floor,
    IntPoint,
    IntPolygon,
    RoomGeometry,
    RoomType,
)


def _rect(
    min_x: int,
    min_y: int,
    max_x: int,
    max_y: int,
) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=min_x, y_mm=min_y),
            IntPoint(x_mm=max_x, y_mm=min_y),
            IntPoint(x_mm=max_x, y_mm=max_y),
            IntPoint(x_mm=min_x, y_mm=max_y),
        )
    )


def _room(
    number: int,
    room_type: RoomType,
    polygon: IntPolygon,
) -> RoomGeometry:
    return RoomGeometry(
        id=UUID(int=number),
        room_type=room_type,
        polygon=polygon,
    )


def _floor(*rooms: RoomGeometry) -> Floor:
    return Floor(
        id=UUID(int=100),
        index=0,
        name="Ground",
        elevation_mm=0,
        floor_to_floor_mm=3000,
        boundary=_rect(0, 0, 10_000, 10_000),
        rooms=rooms,
    )


def test_fully_partitioned_envelope_has_no_unexplained_residual() -> None:
    envelope = _rect(0, 0, 10_000, 10_000)
    floor = _floor(
        _room(1, RoomType.LIVING, _rect(0, 0, 5_000, 10_000)),
        _room(2, RoomType.BEDROOM, _rect(5_000, 0, 10_000, 10_000)),
    )

    analysis = analyze_floor_site_accounting(
        envelope=envelope,
        floor=floor,
        solver_step_mm=10,
    )

    assert analysis.accounting.allocation_basis_points == 10_000
    assert analysis.accounting.residual_area_mm2 == 0
    assert analysis.unexplained_residual_area_mm2 == 0

    require_geometric_site_accounting_closed(analysis)


def test_large_blank_rectangle_is_unexplained_residual() -> None:
    envelope = _rect(0, 0, 10_000, 10_000)
    floor = _floor(
        _room(1, RoomType.LIVING, _rect(0, 0, 5_000, 10_000)),
    )

    analysis = analyze_floor_site_accounting(
        envelope=envelope,
        floor=floor,
        solver_step_mm=10,
    )

    assert analysis.accounting.residual_area_mm2 == 50_000_000
    assert analysis.unexplained_residual_area_mm2 > 49_000_000
    assert len(analysis.residual_regions) == 1

    with pytest.raises(
        ValueError,
        match="Unexplained geometric site residual",
    ):
        require_geometric_site_accounting_closed(analysis)


def test_multiple_blank_regions_remain_visible_as_geometry() -> None:
    envelope = _rect(0, 0, 10_000, 10_000)

    # A full-width occupied band splits the unallocated site into two
    # genuinely disconnected residual polygons: one above and one below.
    floor = _floor(
        _room(
            1,
            RoomType.LIVING,
            _rect(0, 4_000, 10_000, 6_000),
        ),
    )

    analysis = analyze_floor_site_accounting(
        envelope=envelope,
        floor=floor,
        solver_step_mm=10,
    )

    assert analysis.accounting.residual_area_mm2 == 80_000_000
    assert analysis.unexplained_residual_area_mm2 > 79_000_000
    assert len(analysis.residual_regions) == 2
    assert all(region.area_mm2 == 40_000_000 for region in analysis.residual_regions)


def test_solver_lattice_edge_residue_is_numerical_not_architectural() -> None:
    # 30 ft = 9144 mm. On the production 10 mm lattice, the largest
    # representable positive x extent is 9140 mm.
    envelope = _rect(0, 0, 9_144, 15_240)
    floor = Floor(
        id=UUID(int=100),
        index=0,
        name="Ground",
        elevation_mm=0,
        floor_to_floor_mm=3000,
        boundary=envelope,
        rooms=(
            _room(
                1,
                RoomType.LIVING,
                _rect(0, 0, 9_140, 15_240),
            ),
        ),
    )

    analysis = analyze_floor_site_accounting(
        envelope=envelope,
        floor=floor,
        solver_step_mm=10,
    )

    assert analysis.accounting.residual_area_mm2 == 60_960
    assert analysis.numerical_tolerance_mm2 >= 60_960
    assert analysis.unexplained_residual_area_mm2 == 0

    require_geometric_site_accounting_closed(analysis)
