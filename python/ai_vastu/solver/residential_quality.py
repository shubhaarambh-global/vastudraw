from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_vastu.plan_schema import RoomType

_BASIS_POINTS = 10_000

_TIGHT_CAP_ROOM_TYPES = {
    RoomType.PARKING,
    RoomType.GARAGE,
}
_SERVICE_CAP_ROOM_TYPES = {
    RoomType.ATTACHED_TOILET,
    RoomType.COMMON_TOILET,
    RoomType.POWDER_ROOM,
    RoomType.BATH,
    RoomType.SERVANT_TOILET,
    RoomType.PUJA,
    RoomType.PANTRY,
    RoomType.STORE,
    RoomType.UTILITY,
    RoomType.LAUNDRY,
}
_CIRCULATION_CAP_ROOM_TYPES = {
    RoomType.LOBBY,
    RoomType.CORRIDOR,
    RoomType.FOYER,
    RoomType.VERANDAH,
}
_MODERATE_CAP_ROOM_TYPES = {
    RoomType.KITCHEN,
    RoomType.DRESSING,
    RoomType.WARDROBE,
    RoomType.STAIRCASE,
    RoomType.LIFT,
}


@dataclass(frozen=True, slots=True)
class RoomAreaBasis:
    room_instance_id: UUID
    room_type: RoomType
    minimum_envelope_area_mm2: int


@dataclass(frozen=True, slots=True)
class RoomAreaTarget:
    room_instance_id: UUID
    minimum_envelope_area_mm2: int
    maximum_auto_target_area_mm2: int
    target_area_mm2: int


def expansion_cap_basis_points(room_type: RoomType) -> int:
    """Maximum automatic room expansion relative to its solver-envelope minimum."""

    if room_type in _TIGHT_CAP_ROOM_TYPES:
        return 10_500
    if room_type in _SERVICE_CAP_ROOM_TYPES:
        return 12_000
    if room_type in _CIRCULATION_CAP_ROOM_TYPES:
        return 13_500
    if room_type in _MODERATE_CAP_ROOM_TYPES:
        return 15_000
    return 19_000


def allocate_room_area_targets(
    rooms: tuple[RoomAreaBasis, ...],
    *,
    desired_total_area_mm2: int,
) -> tuple[RoomAreaTarget, ...]:
    """Distribute an automatic planning-footprint target deterministically.

    The room minimums remain authoritative hard minima. Automatic expansion is capped by
    room role so parking/service/circulation spaces cannot absorb arbitrary residual area.
    This is a planning heuristic only; it is not an FSI, setback or regulatory entitlement.
    """

    if not rooms:
        return ()
    if desired_total_area_mm2 <= 0:
        raise ValueError("desired_total_area_mm2 must be positive.")

    ordered = tuple(sorted(rooms, key=lambda item: str(item.room_instance_id)))
    bases = {item.room_instance_id: item.minimum_envelope_area_mm2 for item in ordered}
    caps = {
        item.room_instance_id: (
            item.minimum_envelope_area_mm2
            * expansion_cap_basis_points(item.room_type)
            // _BASIS_POINTS
        )
        for item in ordered
    }

    minimum_total = sum(bases.values())
    maximum_total = sum(caps.values())
    effective_total = min(max(desired_total_area_mm2, minimum_total), maximum_total)
    extra = effective_total - minimum_total
    total_capacity = maximum_total - minimum_total

    targets = dict(bases)
    if extra > 0 and total_capacity > 0:
        allocations: list[tuple[UUID, int, int]] = []
        assigned = 0
        for item in ordered:
            room_id = item.room_instance_id
            capacity = caps[room_id] - bases[room_id]
            numerator = extra * capacity
            quotient, remainder = divmod(numerator, total_capacity)
            targets[room_id] += quotient
            assigned += quotient
            allocations.append((room_id, capacity, remainder))

        remainder_units = extra - assigned
        for room_id, capacity, _ in sorted(
            allocations,
            key=lambda item: (-item[2], str(item[0])),
        ):
            if remainder_units <= 0:
                break
            if capacity <= 0 or targets[room_id] >= caps[room_id]:
                continue
            targets[room_id] += 1
            remainder_units -= 1

    return tuple(
        RoomAreaTarget(
            room_instance_id=item.room_instance_id,
            minimum_envelope_area_mm2=bases[item.room_instance_id],
            maximum_auto_target_area_mm2=caps[item.room_instance_id],
            target_area_mm2=targets[item.room_instance_id],
        )
        for item in ordered
    )
