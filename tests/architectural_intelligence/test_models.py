from __future__ import annotations

from ai_vastu.architectural_intelligence.models import (
    ArchitecturalDesignIntent,
    RoomArchitecturalIntent,
    SpaceZone,
)

from .helpers import confirmed


def test_design_intent_hash_is_deterministic() -> None:
    source = confirmed()
    intent = ArchitecturalDesignIntent(
        project_id=source.project_id,
        draft_id=source.draft_id,
        provider="fixture",
        model=None,
        strategy_summary="Functional planning first.",
        room_intents=(
            RoomArchitecturalIntent(
                room_type="living",
                zone=SpaceZone.PUBLIC,
                rationale="Public day zone.",
            ),
        ),
    ).with_content_hash()

    repeated = intent.model_copy(update={"content_hash": None}).with_content_hash()
    assert intent.content_hash == repeated.content_hash
    assert intent.content_hash == intent.compute_content_hash()
