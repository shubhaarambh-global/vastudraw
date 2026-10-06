from __future__ import annotations

from ai_vastu.plan_schema import RoomType
from ai_vastu.validation import validate_architectural_geometry

from .helpers import validation_request


def _error_codes(request) -> set[str]:
    result = validate_architectural_geometry(request)
    return {item.message_code for item in result.report.errors}


def test_valid_architectural_geometry_passes_fail_closed_gate() -> None:
    request = validation_request()
    first = validate_architectural_geometry(request)
    second = validate_architectural_geometry(request)
    assert first.report.valid is True
    assert first.report.errors == ()
    assert first.content_hash == second.content_hash
    assert first == second


def test_missing_exterior_access_makes_rooms_unreachable() -> None:
    request = validation_request(include_access=False)
    assert "UNREACHABLE_ROOM_FROM_EXTERIOR_ACCESS" in _error_codes(request)


def test_swinging_door_requires_explicit_clearance_context() -> None:
    request = validation_request(include_swing_context=False)
    assert "SWINGING_DOOR_REQUIRES_EXPLICIT_CLEARANCE_CONTEXT" in _error_codes(request)


def test_wall_thickness_adjusted_clear_width_is_enforced() -> None:
    request = validation_request(min_width_mm=3900)
    assert "ROOM_CLEAR_WIDTH_BELOW_MINIMUM" in _error_codes(request)


def test_final_validation_rejects_dining_access_through_bedroom() -> None:
    request = validation_request()
    floor = request.geometry.floor
    # The exterior entry belongs to the first room; the second has only an internal door.
    first = next(room for room in floor.rooms if room.room_type is RoomType.LIVING)
    second = next(room for room in floor.rooms if room.room_type is RoomType.DINING)
    changed_floor = floor.model_copy(update={
        "rooms": (first.model_copy(update={"room_type": RoomType.BEDROOM}), second),
    })
    changed = request.model_copy(update={
        "geometry": request.geometry.model_copy(update={"floor": changed_floor}),
    })
    result = validate_architectural_geometry(changed)
    disconnected = [item for item in result.report.errors
                    if item.message_code == "UNREACHABLE_ROOM_FROM_EXTERIOR_ACCESS"]
    assert {room_id for item in disconnected for room_id in item.entity_refs} == {second.id}
