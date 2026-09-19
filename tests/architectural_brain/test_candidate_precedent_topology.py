from uuid import UUID

from ai_vastu.architectural_brain.precedent_topology import (
    bind_precedent_topologies,
    topology_signature,
)
from ai_vastu.architectural_brain.topology import (
    build_fallback_concept,
)
from ai_vastu.precedents import PrecedentMatch

PROJECT_ID = UUID("11111111-2222-3333-4444-555555555555")

ROOM_TYPES = (
    "living",
    "kitchen",
    "lobby",
    "bedroom",
    "parking",
    "puja",
    "common_toilet",
)


def _match(
    precedent_id: str,
    topology_signature_value: str,
    pair_counts: tuple[
        tuple[str, int],
        ...,
    ],
) -> PrecedentMatch:
    return PrecedentMatch(
        precedent_id=precedent_id,
        source_index=1,
        score_basis_points=9_000,
        metric_area_m2=120.0,
        width_m=9.0,
        depth_m=14.0,
        aspect_ratio=14.0 / 9.0,
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
        pair_counts=pair_counts,
        topology_signature=topology_signature_value,
    )


def test_fallback_topology_families_are_not_identical() -> None:
    concepts = tuple(
        build_fallback_concept(
            project_id=PROJECT_ID,
            room_types=ROOM_TYPES,
            ordinal=index,
        )
        for index in range(4)
    )

    signatures = {topology_signature(concept.topology) for concept in concepts}

    assert len(signatures) == 4


def test_distinct_resplan_graph_is_bound_per_candidate() -> None:
    concepts = tuple(
        build_fallback_concept(
            project_id=PROJECT_ID,
            room_types=ROOM_TYPES,
            ordinal=index,
        )
        for index in range(2)
    )

    matches = (
        _match(
            "precedent-a",
            "source-sig-a",
            (
                (
                    "living|via_door|kitchen",
                    1,
                ),
                (
                    "living|adjacency|bedroom",
                    1,
                ),
            ),
        ),
        _match(
            "precedent-b",
            "source-sig-b",
            (
                (
                    "living|via_door|lobby",
                    1,
                ),
                (
                    "kitchen|adjacency|bedroom",
                    1,
                ),
            ),
        ),
    )

    bound = bind_precedent_topologies(
        concepts,
        matches,
    )

    assert bound[0].precedent_ids == ("precedent-a",)
    assert bound[1].precedent_ids == ("precedent-b",)

    assert topology_signature(bound[0].topology) != topology_signature(bound[1].topology)

    assert any(
        "source_topology_signature=source-sig-a" in line for line in bound[0].design_rationale
    )

    assert any(
        "source_topology_signature=source-sig-b" in line for line in bound[1].design_rationale
    )


def test_duplicate_resplan_signature_is_not_reused() -> None:
    concepts = tuple(
        build_fallback_concept(
            project_id=PROJECT_ID,
            room_types=ROOM_TYPES,
            ordinal=index,
        )
        for index in range(2)
    )

    matches = (
        _match(
            "precedent-a",
            "same-source-topology",
            (
                (
                    "living|via_door|kitchen",
                    1,
                ),
            ),
        ),
        _match(
            "precedent-b",
            "same-source-topology",
            (
                (
                    "living|via_door|kitchen",
                    1,
                ),
            ),
        ),
    )

    bound = bind_precedent_topologies(
        concepts,
        matches,
    )

    assert bound[0].precedent_ids == ("precedent-a",)

    # Second candidate must fall back to its own deterministic
    # topology family instead of pretending a duplicate precedent
    # is independent evidence.
    assert bound[1].precedent_ids == ()

    assert topology_signature(bound[0].topology) != topology_signature(bound[1].topology)


def test_resplan_bathroom_semantics_are_not_imported() -> None:
    concepts = (
        build_fallback_concept(
            project_id=PROJECT_ID,
            room_types=ROOM_TYPES,
            ordinal=0,
        ),
    )

    match = _match(
        "precedent-a",
        "bathroom-source",
        (
            (
                "living|via_door|bathroom",
                1,
            ),
            (
                "living|via_door|kitchen",
                1,
            ),
        ),
    )

    bound = bind_precedent_topologies(
        concepts,
        (match,),
    )

    pairs = {
        frozenset(
            (
                edge.source_room_type,
                edge.target_room_type,
            )
        )
        for edge in bound[0].topology
    }

    assert frozenset(
        (
            "living",
            "common_toilet",
        )
    ) not in {
        pair
        for pair in pairs
        if pair
        == frozenset(
            (
                "living",
                "common_toilet",
            )
        )
        and any(
            edge.relation == "DOOR"
            and frozenset(
                (
                    edge.source_room_type,
                    edge.target_room_type,
                )
            )
            == pair
            for edge in bound[0].topology
        )
    }
