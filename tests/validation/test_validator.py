from __future__ import annotations

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
