from __future__ import annotations

import hashlib
from typing import Literal

from ai_vastu.precedents import PrecedentMatch

from .models import (
    ArchitecturalConcept,
    TopologyEdge,
)
from .topology import residential_topology_family

_RESPLAN_ROOM_TYPE_MAP: dict[str, str] = {
    "living": "living",
    "kitchen": "kitchen",
    "bedroom": "bedroom",
    "storage": "store",
    "stair": "staircase",
    "balcony": "balcony",
    "parking": "parking",
}

_SUPPORTED_RELATIONSHIPS = frozenset(
    {
        "direct",
        "via_door",
        "adjacency",
    }
)


def _normalized_room_type(
    value: str,
) -> str | None:
    return _RESPLAN_ROOM_TYPE_MAP.get(value.strip().lower())


def _edge_pair_key(
    edge: TopologyEdge,
) -> tuple[str, str]:
    ordered = sorted(
        (
            edge.source_room_type,
            edge.target_room_type,
        )
    )
    return (
        ordered[0],
        ordered[1],
    )


def topology_signature(
    edges: tuple[TopologyEdge, ...],
) -> str:
    """Stable semantic signature independent of edge ordering."""

    encoded = tuple(
        sorted(
            (
                *_edge_pair_key(edge),
                edge.relation,
                edge.weight,
            )
            for edge in edges
        )
    )

    payload = repr(encoded).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def precedent_topology_edges(
    match: PrecedentMatch,
    *,
    present_room_types: frozenset[str],
) -> tuple[TopologyEdge, ...]:
    """Translate one ResPlan graph into one candidate topology.

    Bathroom topology is intentionally excluded because ResPlan cannot
    distinguish attached/common/powder semantics.
    """

    strongest: dict[
        tuple[str, str],
        TopologyEdge,
    ] = {}

    relation_rank = {
        "DOOR": 3,
        "ADJACENT": 2,
        "NEAR": 1,
    }

    for encoded, _count in match.pair_counts:
        parts = encoded.split("|")

        if len(parts) != 3:
            continue

        left_raw, relationship, right_raw = parts

        if relationship not in _SUPPORTED_RELATIONSHIPS:
            continue

        if left_raw == "bathroom" or right_raw == "bathroom":
            continue

        left = _normalized_room_type(left_raw)
        right = _normalized_room_type(right_raw)

        if (
            left is None
            or right is None
            or left == right
            or left not in present_room_types
            or right not in present_room_types
        ):
            continue

        relation: Literal["DOOR", "ADJACENT"]

        if relationship in {
            "direct",
            "via_door",
        }:
            relation = "DOOR"
            weight = 100
        else:
            relation = "ADJACENT"
            weight = 90

        edge = TopologyEdge(
            source_room_type=left,
            target_room_type=right,
            relation=relation,
            weight=weight,
        )

        key = _edge_pair_key(edge)
        prior = strongest.get(key)

        if (
            prior is None
            or relation_rank[edge.relation] > relation_rank[prior.relation]
            or (
                relation_rank[edge.relation] == relation_rank[prior.relation]
                and edge.weight > prior.weight
            )
        ):
            strongest[key] = edge

    return tuple(
        sorted(
            strongest.values(),
            key=lambda edge: (
                *_edge_pair_key(edge),
                edge.relation,
                -edge.weight,
            ),
        )
    )


def _merge_candidate_topology(
    *,
    precedent_edges: tuple[TopologyEdge, ...],
    concept_edges: tuple[TopologyEdge, ...],
    fallback_edges: tuple[TopologyEdge, ...],
) -> tuple[TopologyEdge, ...]:
    """Merge by authority: precedent -> concept -> deterministic family.

    One semantic relation is retained for each unordered room-type pair.
    This prevents a candidate from simultaneously asking two rooms to be
    adjacent and avoided.
    """

    merged: list[TopologyEdge] = []
    used_pairs: set[tuple[str, str]] = set()

    for collection in (
        precedent_edges,
        concept_edges,
        fallback_edges,
    ):
        for edge in collection:
            if edge.source_room_type == edge.target_room_type:
                continue

            key = _edge_pair_key(edge)

            if key in used_pairs:
                continue

            used_pairs.add(key)
            merged.append(edge)

    return tuple(merged)


def _distinct_precedents(
    matches: tuple[
        PrecedentMatch,
        ...,
    ],
) -> tuple[
    PrecedentMatch,
    ...,
]:
    seen: set[str] = set()
    distinct: list[PrecedentMatch] = []

    for match in matches:
        key = match.topology_signature.strip() or f"precedent:{match.precedent_id}"

        if key in seen:
            continue

        seen.add(key)
        distinct.append(match)

    return tuple(distinct)


def bind_precedent_topologies(
    concepts: tuple[
        ArchitecturalConcept,
        ...,
    ],
    matches: tuple[
        PrecedentMatch,
        ...,
    ],
) -> tuple[
    ArchitecturalConcept,
    ...,
]:
    """Give each candidate a distinct topology before geometry solving."""

    distinct_matches = _distinct_precedents(matches)

    bound: list[ArchitecturalConcept] = []

    for index, concept in enumerate(concepts):
        present = frozenset(
            room.room_type.strip().lower().replace(" ", "_") for room in concept.rooms
        )

        fallback_edges = residential_topology_family(
            tuple(sorted(present)),
            ordinal=index,
        )

        match = distinct_matches[index] if index < len(distinct_matches) else None

        if match is None:
            merged = _merge_candidate_topology(
                precedent_edges=(),
                concept_edges=concept.topology,
                fallback_edges=fallback_edges,
            )

            rationale = (
                *concept.design_rationale,
                (
                    "No additional distinct ResPlan topology was "
                    "available for this candidate; deterministic "
                    f"topology family {index % 4} was applied."
                ),
                (f"Candidate topology signature={topology_signature(merged)}."),
            )

            bound.append(
                concept.model_copy(
                    update={
                        "topology": merged,
                        "precedent_ids": (),
                        "design_rationale": rationale,
                        "content_hash": None,
                    }
                ).with_content_hash()
            )
            continue

        precedent_edges = precedent_topology_edges(
            match,
            present_room_types=present,
        )

        merged = _merge_candidate_topology(
            precedent_edges=precedent_edges,
            concept_edges=concept.topology,
            fallback_edges=fallback_edges,
        )

        rationale = (
            *concept.design_rationale,
            (
                "Candidate-specific ResPlan precedent="
                f"{match.precedent_id}; "
                "source_topology_signature="
                f"{match.topology_signature}."
            ),
            (f"Candidate topology signature={topology_signature(merged)}."),
        )

        bound.append(
            concept.model_copy(
                update={
                    "topology": merged,
                    "precedent_ids": (match.precedent_id,),
                    "design_rationale": rationale,
                    "content_hash": None,
                }
            ).with_content_hash()
        )

    return tuple(bound)
