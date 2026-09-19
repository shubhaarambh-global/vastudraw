from ai_vastu.architectural_brain.candidate_engine import (
    _unique_adjacency_preferences,
)
from ai_vastu.plan_schema import (
    AdjacencyPreference,
    RoomType,
)


def test_duplicate_target_keeps_earlier_layer() -> None:
    precedent = AdjacencyPreference(
        target_room_type=RoomType.KITCHEN,
        weight=45,
        max_gap_mm=1800,
    )

    late_brain = AdjacencyPreference(
        target_room_type=RoomType.KITCHEN,
        weight=95,
        max_gap_mm=300,
        min_shared_length_mm=800,
    )

    result = _unique_adjacency_preferences(
        (
            precedent,
            late_brain,
        )
    )

    assert result == (precedent,)


def test_different_targets_are_preserved() -> None:
    kitchen = AdjacencyPreference(
        target_room_type=RoomType.KITCHEN,
        weight=60,
    )

    bedroom = AdjacencyPreference(
        target_room_type=RoomType.BEDROOM,
        weight=70,
    )

    result = _unique_adjacency_preferences(
        (
            kitchen,
            bedroom,
        )
    )

    assert result == (
        kitchen,
        bedroom,
    )
