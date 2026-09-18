from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema import RoomType
from ai_vastu.solver.residential_quality import (
    RoomAreaBasis,
    allocate_room_area_targets,
    expansion_cap_basis_points,
)


def test_auto_area_distribution_caps_parking_before_habitable_rooms() -> None:
    rooms = (
        RoomAreaBasis(
            room_instance_id=UUID("10000000-0000-0000-0000-000000000001"),
            room_type=RoomType.LIVING,
            minimum_envelope_area_mm2=12_000_000,
        ),
        RoomAreaBasis(
            room_instance_id=UUID("10000000-0000-0000-0000-000000000002"),
            room_type=RoomType.BEDROOM,
            minimum_envelope_area_mm2=10_000_000,
        ),
        RoomAreaBasis(
            room_instance_id=UUID("10000000-0000-0000-0000-000000000003"),
            room_type=RoomType.PARKING,
            minimum_envelope_area_mm2=12_500_000,
        ),
    )

    targets = allocate_room_area_targets(
        rooms,
        desired_total_area_mm2=55_000_000,
    )
    by_id = {item.room_instance_id: item for item in targets}

    parking = by_id[rooms[2].room_instance_id]
    living = by_id[rooms[0].room_instance_id]
    assert expansion_cap_basis_points(RoomType.PARKING) == 10_500
    assert parking.target_area_mm2 <= 13_125_000
    assert living.target_area_mm2 > living.minimum_envelope_area_mm2
    assert sum(item.target_area_mm2 for item in targets) <= 55_000_000


def test_auto_area_distribution_is_deterministic() -> None:
    rooms = (
        RoomAreaBasis(
            room_instance_id=UUID("20000000-0000-0000-0000-000000000002"),
            room_type=RoomType.KITCHEN,
            minimum_envelope_area_mm2=7_000_000,
        ),
        RoomAreaBasis(
            room_instance_id=UUID("20000000-0000-0000-0000-000000000001"),
            room_type=RoomType.BEDROOM,
            minimum_envelope_area_mm2=10_000_000,
        ),
    )

    first = allocate_room_area_targets(
        rooms,
        desired_total_area_mm2=25_000_000,
    )
    second = allocate_room_area_targets(
        tuple(reversed(rooms)),
        desired_total_area_mm2=25_000_000,
    )

    assert first == second
