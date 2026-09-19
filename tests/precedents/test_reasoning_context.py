from __future__ import annotations

from ai_vastu.precedents import PrecedentMatch
from ai_vastu.requirements.precedent_adapter import (
    precedent_reasoning_context,
)


def _match() -> PrecedentMatch:
    return PrecedentMatch(
        precedent_id="resplan-1",
        source_index=1,
        score_basis_points=9750,
        metric_area_m2=125.0,
        width_m=15.2,
        depth_m=9.1,
        aspect_ratio=1.67,
        living_count=1,
        bedroom_count=2,
        bathroom_count=2,
        kitchen_count=1,
        balcony_count=0,
        storage_count=0,
        stair_count=0,
        parking_count=1,
        door_count=8,
        window_count=7,
        front_door_count=1,
        entry_room_types=("living",),
        nodes=(),
        edges=(),
        pair_counts=(
            (
                "bedroom|via_door|living",
                2,
            ),
            (
                "kitchen|via_door|living",
                1,
            ),
        ),
        topology_signature="topology-1",
    )


def test_reasoning_context_preserves_precedent_evidence() -> None:
    context = precedent_reasoning_context((_match(),))

    assert len(context) == 1

    precedent = context[0]

    assert precedent["precedent_id"] == "resplan-1"
    assert precedent["similarity_basis_points"] == 9750
    assert precedent["entry_room_types"] == ("living",)

    relationships = precedent["relationship_counts"]

    assert isinstance(
        relationships,
        dict,
    )

    assert relationships["bedroom|via_door|living"] == 2


def test_empty_precedents_produce_empty_context() -> None:
    assert precedent_reasoning_context(()) == ()
