"""Access checks for physical changes to saved single-floor confirmed plans."""

from collections import Counter

from ai_vastu.architectural_geometry import validate_circulation
from ai_vastu.plan_schema import PlanDocument

from .vehicle_access import validate_document_vehicle_access


def _physical_signature(document: PlanDocument) -> tuple[object, ...]:
    floors = tuple(
        (
            floor.index,
            tuple(
                sorted(
                    (str(room.id), room.room_type.value, room.polygon.model_dump_json())
                    for room in floor.rooms
                )
            ),
            tuple(sorted(wall.model_dump_json() for wall in floor.walls)),
            tuple(sorted(opening.model_dump_json() for opening in floor.openings)),
            tuple(sorted(stair.model_dump_json() for stair in floor.stairs)),
        )
        for floor in sorted(document.floors, key=lambda item: item.index)
    )
    return (
        document.plot.boundary.model_dump_json(),
        tuple(road.model_dump_json() for road in document.roads),
        floors,
    )


def validate_changed_revision_access(*, prior: PlanDocument, document: PlanDocument) -> None:
    """Fail closed on new physical access defects without requalifying legacy snapshots.

    This bounded guard covers single-floor confirmed plans. Existing multi-floor
    qualification, initial imports, and geometry-identical snapshots keep their
    existing contracts; this is not a replacement for full architectural validation.
    """
    if not any(
        item.code == "PHASE24_CONFIRMED_CONTEXT" and item.confirmed_by_user
        for plan in (prior, document)
        for item in plan.assumptions
    ):
        return
    if len(prior.floors) != 1 or len(document.floors) != 1:
        return
    if _physical_signature(prior) == _physical_signature(document):
        return
    old_bays = Counter(
        room.room_type
        for room in prior.floors[0].rooms
        if room.room_type.value in {"parking", "garage"}
    )
    new_bays = Counter(
        room.room_type
        for room in document.floors[0].rooms
        if room.room_type.value in {"parking", "garage"}
    )
    if old_bays - new_bays:
        raise ValueError("VEHICLE_ACCESS_INVALID: Saved vehicle bays cannot be removed.")
    circulation = validate_circulation(document.floors[0])
    if not circulation.accepted:
        raise ValueError(f"{circulation.reason_code}: Changed saved plan has invalid room access.")
    if validate_document_vehicle_access(document):
        raise ValueError("VEHICLE_ACCESS_INVALID: Changed saved plan lacks usable vehicle access.")
