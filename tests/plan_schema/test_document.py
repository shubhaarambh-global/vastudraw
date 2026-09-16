import json

import pytest
from pydantic import ValidationError

from ai_vastu.plan_schema import IntPoint, IntPolygon, PlanDocument

from .sample import sample_plan


def test_document_is_immutable() -> None:
    plan = sample_plan()
    with pytest.raises(ValidationError):
        plan.canonical_units = "cm"  # type: ignore[misc,assignment]


def test_polygon_ring_is_tuple_and_cannot_be_appended() -> None:
    plan = sample_plan()
    assert isinstance(plan.plot.boundary.outer, tuple)
    with pytest.raises(AttributeError):
        plan.plot.boundary.outer.append(IntPoint(x_mm=1, y_mm=1))  # type: ignore[attr-defined]


def test_polygon_rejects_explicit_closing_vertex() -> None:
    p0 = IntPoint(x_mm=0, y_mm=0)
    with pytest.raises(ValidationError, match="stored open"):
        IntPolygon(
            outer=(
                p0,
                IntPoint(x_mm=100, y_mm=0),
                IntPoint(x_mm=100, y_mm=100),
                p0,
            )
        )


def test_canonical_hash_is_stable_across_round_trip() -> None:
    plan = sample_plan().with_content_hash()
    payload = plan.to_canonical_json()
    parsed = PlanDocument.model_validate_json(payload)
    assert parsed.content_hash == plan.content_hash
    assert parsed.compute_content_hash() == plan.compute_content_hash()
    assert parsed.to_canonical_json() == payload


def test_tampered_hash_is_rejected() -> None:
    plan = sample_plan().with_content_hash()
    payload = json.loads(plan.to_canonical_json())
    payload["content_hash"] = "0" * 64
    with pytest.raises(ValidationError, match="does not match"):
        PlanDocument.model_validate(payload, strict=False)


def test_unknown_fields_fail_closed() -> None:
    payload = json.loads(sample_plan().to_canonical_json())
    payload["unexpected"] = True
    with pytest.raises(ValidationError, match="extra_forbidden"):
        PlanDocument.model_validate(payload, strict=False)


def test_floor_owned_entities_are_not_duplicated_at_root() -> None:
    fields = PlanDocument.model_fields
    assert "rooms" not in fields
    assert "walls" not in fields
    assert "openings" not in fields


def test_integer_coordinates_reject_binary_float() -> None:
    with pytest.raises(ValidationError):
        IntPoint(x_mm=1.0, y_mm=0)  # type: ignore[arg-type]
