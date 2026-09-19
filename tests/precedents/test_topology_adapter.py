from __future__ import annotations

from ai_vastu.plan_schema import RoomType
from ai_vastu.precedents import (
    PrecedentMatch,
)
from ai_vastu.requirements.precedent_adapter import (
    derive_topology_evidence,
)


def _match(
    *,
    precedent_id: str,
    pairs: tuple[tuple[str, int], ...],
) -> PrecedentMatch:
    return PrecedentMatch(
        precedent_id=precedent_id,
        source_index=1,
        score_basis_points=9000,
        metric_area_m2=120.0,
        width_m=15.0,
        depth_m=9.0,
        aspect_ratio=1.666,
        living_count=1,
        bedroom_count=2,
        bathroom_count=2,
        kitchen_count=1,
        balcony_count=0,
        storage_count=0,
        stair_count=0,
        parking_count=1,
        door_count=8,
        window_count=6,
        front_door_count=1,
        entry_room_types=("living",),
        nodes=(),
        edges=(),
        pair_counts=pairs,
        topology_signature=precedent_id,
    )


def test_majority_relationship_becomes_evidence() -> None:
    matches = (
        _match(
            precedent_id="a",
            pairs=(
                (
                    "kitchen|via_door|living",
                    1,
                ),
            ),
        ),
        _match(
            precedent_id="b",
            pairs=(
                (
                    "kitchen|direct|living",
                    1,
                ),
            ),
        ),
        _match(
            precedent_id="c",
            pairs=(
                (
                    "bedroom|via_door|living",
                    2,
                ),
            ),
        ),
    )

    evidence = derive_topology_evidence(matches)

    kitchen_living = next(
        item
        for item in evidence
        if {
            item.source_room_type,
            item.target_room_type,
        }
        == {
            RoomType.KITCHEN,
            RoomType.LIVING,
        }
    )

    assert kitchen_living.support_count == 2
    assert kitchen_living.precedent_count == 3
    assert kitchen_living.weight <= 55


def test_ambiguous_resplan_bathroom_is_not_imported() -> None:
    matches = (
        _match(
            precedent_id="a",
            pairs=(
                (
                    "bathroom|via_door|bedroom",
                    2,
                ),
            ),
        ),
        _match(
            precedent_id="b",
            pairs=(
                (
                    "bathroom|adjacency|living",
                    1,
                ),
            ),
        ),
    )

    evidence = derive_topology_evidence(matches)

    assert evidence == ()


def test_single_precedent_outlier_does_not_control_topology() -> None:
    matches = (
        _match(
            precedent_id="a",
            pairs=(
                (
                    "kitchen|via_door|living",
                    1,
                ),
            ),
        ),
        _match(
            precedent_id="b",
            pairs=(),
        ),
        _match(
            precedent_id="c",
            pairs=(),
        ),
        _match(
            precedent_id="d",
            pairs=(),
        ),
    )

    evidence = derive_topology_evidence(matches)

    assert evidence == ()
