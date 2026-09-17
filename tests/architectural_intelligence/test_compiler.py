from __future__ import annotations

from ai_vastu.architectural_intelligence import (
    ArchitecturalReasoningInput,
    apply_design_intent,
)
from ai_vastu.architectural_intelligence.providers.fixture import (
    FixtureArchitecturalIntelligenceProvider,
)
from ai_vastu.requirements.generation_adapter import compile_confirmed_requirements

from .helpers import confirmed


def test_design_intent_changes_soft_preferences_not_hard_minimums() -> None:
    source = confirmed()
    base = compile_confirmed_requirements(source)
    intent = FixtureArchitecturalIntelligenceProvider().reason(
        ArchitecturalReasoningInput(
            confirmed=source,
            original_prompt="Both bedrooms need wardrobe space.",
        )
    )
    enriched = apply_design_intent(base, intent)

    base_by_type = {item.room_type.value: item for item in base.request.room_requirements}
    enriched_by_type = {item.room_type.value: item for item in enriched.request.room_requirements}

    for room_type, original in base_by_type.items():
        current = enriched_by_type[room_type]
        assert current.min_width_mm == original.min_width_mm
        assert current.min_depth_mm == original.min_depth_mm
        assert current.min_area_mm2 == original.min_area_mm2
        assert current.max_width_mm == original.max_width_mm
        assert current.max_depth_mm == original.max_depth_mm
        assert current.max_area_mm2 == original.max_area_mm2

    assert enriched_by_type["living"].adjacency_preferences
    assert enriched_by_type["dining"].adjacency_preferences
    assert any(not item.hard for item in enriched_by_type["living"].adjacency_prohibitions)
    assert any("soft preferences only" in notice for notice in enriched.notices)
