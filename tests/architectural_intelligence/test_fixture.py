from __future__ import annotations

from ai_vastu.architectural_intelligence import (
    ArchitecturalReasoningInput,
    FeatureKind,
    RelationshipKind,
)
from ai_vastu.architectural_intelligence.providers.fixture import (
    FixtureArchitecturalIntelligenceProvider,
)

from .helpers import confirmed


def test_fixture_captures_relationships_and_wardrobe_feature() -> None:
    source = confirmed()
    intent = FixtureArchitecturalIntelligenceProvider().reason(
        ArchitecturalReasoningInput(
            confirmed=source,
            original_prompt=(
                "2BHK home. Both bedrooms need wardrobe space. Keep kitchen convenient to dining."
            ),
        )
    )

    assert intent.project_id == source.project_id
    assert intent.draft_id == source.draft_id
    assert intent.content_hash is not None

    pairs = {
        (
            item.source_room_type,
            item.target_room_type,
            item.kind,
        )
        for item in intent.relationships
    }
    assert ("living", "dining", RelationshipKind.ADJACENT) in pairs
    assert ("dining", "kitchen", RelationshipKind.DIRECT_ACCESS) in pairs

    bedroom = next(item for item in intent.room_intents if item.room_type == "bedroom")
    assert any(feature.kind is FeatureKind.WARDROBE_WALL for feature in bedroom.features)
