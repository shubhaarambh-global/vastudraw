from uuid import UUID

import pytest
from tests.requirements.test_phase26c4a_residential_planning import _confirmed

from ai_vastu.architectural_brain import (
    SpaceAllocation,
    build_fallback_concept,
    close_site_accounting,
    default_source_registry,
    deterministic_revision_interpretation,
    require_no_unexplained_residual,
)
from ai_vastu.architectural_brain.bridge import apply_architectural_concept
from ai_vastu.requirements.generation_adapter import compile_confirmed_requirements


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


def test_brain_concept_size_caps_remain_non_authoritative_preferences() -> None:
    compiled = compile_confirmed_requirements(_confirmed())
    concept = build_fallback_concept(
        project_id=compiled.request.floor_id,
        room_types=tuple(
            requirement.room_type.value
            for requirement in compiled.request.room_requirements
        ),
    )

    updated = apply_architectural_concept(compiled, concept)
    parking = next(
        requirement
        for requirement in updated.request.room_requirements
        if requirement.room_type.value == "parking"
    )

    assert parking.preferred_area_mm2 == 16_500_000
    assert parking.max_area_mm2 is None
    assert any(
        "non_authoritative_hard_size_caps_ignored=" in notice
        for notice in updated.notices
    )


def test_revision_interpreter_understands_one_foot_wider() -> None:
    intent = deterministic_revision_interpretation(
        project_id=UUID("11111111-1111-1111-1111-111111111111"),
        base_revision_id=UUID("22222222-2222-2222-2222-222222222222"),
        request="Make dining 1 ft wider",
    )
    assert intent.directives[0].room_type == "dining"
    assert intent.directives[0].axis == "WIDTH"
    assert intent.directives[0].delta_mm == 305
