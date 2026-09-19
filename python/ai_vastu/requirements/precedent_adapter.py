from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ai_vastu.plan_schema import (
    AdjacencyPreference,
    RoomRequirement,
    RoomType,
)
from ai_vastu.precedents import (
    PrecedentMatch,
    PrecedentQuery,
    ResPlanPrecedentStore,
    resplan_precedents_enabled,
)

from .generation_adapter import CompiledGeneration
from .models import ConfirmedRequirements

# ResPlan semantics that map cleanly to Vastudraw V1 semantics.
#
# Bathroom is deliberately excluded. ResPlan does not distinguish
# attached/common/bath/powder semantics, therefore importing bathroom
# topology would invent information that the precedent does not contain.
_RESPLAN_ROOM_TYPE_MAP: dict[str, RoomType] = {
    "living": RoomType.LIVING,
    "kitchen": RoomType.KITCHEN,
    "bedroom": RoomType.BEDROOM,
    "storage": RoomType.STORE,
    "stair": RoomType.STAIRCASE,
    "balcony": RoomType.BALCONY,
    "parking": RoomType.PARKING,
}

_SANITARY_NAMES = frozenset(
    {
        "bathroom",
        "attached_toilet",
        "common_toilet",
        "powder_room",
        "bath",
        "servant_toilet",
    }
)

_SUPPORTED_RELATIONSHIPS = frozenset(
    {
        "direct",
        "via_door",
        "adjacency",
    }
)


@dataclass(frozen=True, slots=True)
class PrecedentTopologyEvidence:
    source_room_type: RoomType
    target_room_type: RoomType
    support_count: int
    precedent_count: int
    relationship_strength: int

    @property
    def support_basis_points(self) -> int:
        if self.precedent_count <= 0:
            return 0
        return self.support_count * 10_000 // self.precedent_count

    @property
    def weight(self) -> int:
        """Low/medium weight: precedent evidence may guide but never dominate."""

        support = self.support_basis_points

        # 50-100% support -> 20-45.
        evidence_weight = 20 + (max(0, support - 5_000) * 25 // 5_000)

        # Door/direct connectivity is stronger topology evidence than
        # geometric wall adjacency alone.
        relationship_bonus = min(
            10,
            self.relationship_strength,
        )

        return min(
            55,
            evidence_weight + relationship_bonus,
        )


def _room_type_name(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw).strip().lower()


def _confirmed_room_count(
    confirmed: ConfirmedRequirements,
    names: frozenset[str],
) -> int:
    return sum(
        int(room.quantity) for room in confirmed.rooms if _room_type_name(room.room_type) in names
    )


def build_precedent_query(
    confirmed: ConfirmedRequirements,
    *,
    limit: int = 6,
) -> PrecedentQuery:
    width_mm = int(confirmed.plot_width_mm)
    depth_mm = int(confirmed.plot_depth_mm)

    shorter = min(width_mm, depth_mm)
    longer = max(width_mm, depth_mm)

    if shorter <= 0:
        raise ValueError("Confirmed plot dimensions must be positive.")

    bathrooms = _confirmed_room_count(
        confirmed,
        _SANITARY_NAMES,
    )

    kitchens = _confirmed_room_count(
        confirmed,
        frozenset({"kitchen"}),
    )

    living_rooms = _confirmed_room_count(
        confirmed,
        frozenset(
            {
                "living",
                "drawing",
                "family_lounge",
            }
        ),
    )

    return PrecedentQuery(
        bedrooms=int(confirmed.bedroom_count),
        bathrooms=max(0, bathrooms),
        kitchens=max(1, kitchens),
        living_rooms=max(1, living_rooms),
        parking_spaces=max(
            0,
            int(confirmed.parking_count),
        ),
        target_aspect_ratio=longer / shorter,
        target_area_m2=(width_mm * depth_mm / 1_000_000),
        limit=limit,
    )


def _precedent_relationships(
    match: PrecedentMatch,
) -> dict[
    tuple[RoomType, RoomType],
    int,
]:
    """Extract one topology vote per room-type pair per precedent."""

    evidence: dict[
        tuple[RoomType, RoomType],
        int,
    ] = {}

    for encoded, _count in match.pair_counts:
        parts = encoded.split("|")

        if len(parts) != 3:
            continue

        left_name, relationship, right_name = parts

        if relationship not in _SUPPORTED_RELATIONSHIPS:
            continue

        # Explicitly refuse ambiguous bathroom semantics.
        if left_name == "bathroom" or right_name == "bathroom":
            continue

        left = _RESPLAN_ROOM_TYPE_MAP.get(left_name)
        right = _RESPLAN_ROOM_TYPE_MAP.get(right_name)

        if left is None or right is None:
            continue

        if left is right:
            continue

        ordered_pair = sorted(
            (left, right),
            key=lambda item: item.value,
        )
        pair: tuple[RoomType, RoomType] = (
            ordered_pair[0],
            ordered_pair[1],
        )

        # Relationship evidence strength:
        # direct / door connection > mere wall adjacency.
        strength = 10 if relationship in {"direct", "via_door"} else 4

        evidence[pair] = max(
            evidence.get(pair, 0),
            strength,
        )

    return evidence


def derive_topology_evidence(
    matches: tuple[PrecedentMatch, ...],
) -> tuple[PrecedentTopologyEvidence, ...]:
    if not matches:
        return ()

    support: Counter[tuple[RoomType, RoomType]] = Counter()

    strength: dict[
        tuple[RoomType, RoomType],
        int,
    ] = {}

    for match in matches:
        relationships = _precedent_relationships(match)

        for pair, relationship_strength in relationships.items():
            support[pair] += 1
            strength[pair] = max(
                strength.get(pair, 0),
                relationship_strength,
            )

    minimum_support = (len(matches) + 1) // 2

    evidence = [
        PrecedentTopologyEvidence(
            source_room_type=pair[0],
            target_room_type=pair[1],
            support_count=count,
            precedent_count=len(matches),
            relationship_strength=strength[pair],
        )
        for pair, count in support.items()
        if count >= minimum_support
    ]

    evidence.sort(
        key=lambda item: (
            -item.support_basis_points,
            -item.relationship_strength,
            item.source_room_type.value,
            item.target_room_type.value,
        )
    )

    return tuple(evidence)


def _apply_relationship(
    *,
    requirement: RoomRequirement,
    target: RoomType,
    weight: int,
) -> RoomRequirement:
    preferences = list(requirement.adjacency_preferences)

    prohibitions = {item.target_room_type for item in requirement.adjacency_prohibitions}

    existing = {item.target_room_type for item in preferences}

    # Never override an explicit/user/architectural prohibition.
    if target in prohibitions:
        return requirement

    # Never duplicate stronger existing evidence.
    if target in existing:
        return requirement

    preferences.append(
        AdjacencyPreference(
            target_room_type=target,
            weight=weight,
            # Near enough to materially influence topology,
            # but not a hard adjacency contract.
            max_gap_mm=1800,
            min_shared_length_mm=None,
        )
    )

    return requirement.model_copy(update={"adjacency_preferences": tuple(preferences)})


def retrieve_resplan_precedents(
    confirmed: ConfirmedRequirements,
    *,
    limit: int = 6,
) -> tuple[PrecedentMatch, ...]:
    """Retrieve diverse real-plan precedents for architectural reasoning."""

    if not resplan_precedents_enabled():
        return ()

    store = ResPlanPrecedentStore.from_environment()

    query = build_precedent_query(
        confirmed,
        limit=limit,
    )

    return store.search(query)


def precedent_reasoning_context(
    matches: tuple[PrecedentMatch, ...],
) -> tuple[dict[str, object], ...]:
    """Create bounded, traceable precedent context for the AI reasoning layer."""

    return tuple(match.architectural_context() for match in matches)


def apply_resplan_precedents(
    compiled: CompiledGeneration,
    confirmed: ConfirmedRequirements,
    *,
    matches: tuple[PrecedentMatch, ...] | None = None,
) -> CompiledGeneration:
    """Inject real-plan topology as traceable soft solver evidence."""

    if not resplan_precedents_enabled():
        return compiled

    if matches is None:
        matches = retrieve_resplan_precedents(
            confirmed,
            limit=6,
        )

    if not matches:
        return CompiledGeneration(
            request=compiled.request,
            profile_version=compiled.profile_version,
            notices=(
                *compiled.notices,
                ("ResPlan precedent retrieval produced no usable residential topology."),
            ),
        )

    evidence = derive_topology_evidence(matches)

    requirements = list(compiled.request.room_requirements)

    present_types = {requirement.room_type for requirement in requirements}

    applied: list[PrecedentTopologyEvidence] = []

    for item in evidence:
        if item.source_room_type not in present_types or item.target_room_type not in present_types:
            continue

        changed = False
        updated_requirements = []

        for requirement in requirements:
            updated = requirement

            if requirement.room_type is item.source_room_type:
                updated = _apply_relationship(
                    requirement=requirement,
                    target=item.target_room_type,
                    weight=item.weight,
                )

            elif requirement.room_type is item.target_room_type:
                updated = _apply_relationship(
                    requirement=requirement,
                    target=item.source_room_type,
                    weight=item.weight,
                )

            if updated != requirement:
                changed = True

            updated_requirements.append(updated)

        if changed:
            requirements = updated_requirements
            applied.append(item)

    precedent_summary = ",".join(
        (f"{item.precedent_id}:{item.score_basis_points}") for item in matches
    )

    relationship_summary = ",".join(
        (
            f"{item.source_room_type.value}"
            f"<->{item.target_room_type.value}"
            f":support={item.support_basis_points}"
            f":weight={item.weight}"
        )
        for item in applied
    )

    request = compiled.request.model_copy(update={"room_requirements": tuple(requirements)})

    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=(
            *compiled.notices,
            (
                "ResPlan precedent topology applied as "
                "non-authoritative soft solver evidence; "
                f"precedents={precedent_summary or 'none'}."
            ),
            (f"ResPlan topology relationships={relationship_summary or 'none'}."),
        ),
    )
