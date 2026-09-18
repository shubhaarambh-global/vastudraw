from uuid import UUID

import pytest

from ai_vastu.architectural_brain import (
    SpaceAllocation,
    build_fallback_concept,
    close_site_accounting,
    default_source_registry,
    deterministic_revision_interpretation,
    require_no_unexplained_residual,
)


def test_source_registry_separates_commercial_and_research_only() -> None:
    registry = {item.source_id: item for item in default_source_registry()}
    assert registry["resplan"].license_id == "CC-BY-4.0"
    assert registry["cubicasa5k"].license_class.value == "RESEARCH_ONLY"


def test_site_accounting_requires_residual_classification() -> None:
    accounting = close_site_accounting(
        envelope_area_mm2=100_000_000,
        allocations=(
            SpaceAllocation(category="ROOM", label="rooms", area_mm2=75_000_000),
            SpaceAllocation(category="PARKING", label="parking", area_mm2=15_000_000),
        ),
    )
    assert accounting.residual_area_mm2 == 10_000_000
    with pytest.raises(ValueError):
        require_no_unexplained_residual(accounting)


def test_brain_concept_is_topology_first_and_non_authoritative() -> None:
    concept = build_fallback_concept(
        project_id=UUID("11111111-1111-1111-1111-111111111111"),
        room_types=(
            "living",
            "dining",
            "kitchen",
            "bedroom",
            "lobby",
            "common_toilet",
            "parking",
            "puja",
        ),
    )
    assert concept.authoritative_geometry is False
    parking = next(room for room in concept.rooms if room.room_type == "parking")
    assert parking.max_area_mm2 == 18_000_000
    assert any(edge.source_room_type == "living" for edge in concept.topology)


def test_revision_interpreter_understands_one_foot_wider() -> None:
    intent = deterministic_revision_interpretation(
        project_id=UUID("11111111-1111-1111-1111-111111111111"),
        base_revision_id=UUID("22222222-2222-2222-2222-222222222222"),
        request="Make dining 1 ft wider",
    )
    assert intent.directives[0].room_type == "dining"
    assert intent.directives[0].axis == "WIDTH"
    assert intent.directives[0].delta_mm == 305
