from __future__ import annotations

from ai_vastu.requirements.generation_profile import normalize_room_type

from ..models import (
    ArchitecturalDesignIntent,
    CirculationIntent,
    FeatureKind,
    RelationshipIntent,
    RelationshipKind,
    RoomArchitecturalIntent,
    RoomFeatureIntent,
    SpaceZone,
)
from .base import ArchitecturalReasoningInput

_ZONE_BY_TYPE: dict[str, SpaceZone] = {
    "living": SpaceZone.PUBLIC,
    "drawing": SpaceZone.PUBLIC,
    "dining": SpaceZone.PUBLIC,
    "foyer": SpaceZone.PUBLIC,
    "verandah": SpaceZone.PUBLIC,
    "family_lounge": SpaceZone.SEMI_PRIVATE,
    "master_bedroom": SpaceZone.PRIVATE,
    "bedroom": SpaceZone.PRIVATE,
    "parents_bedroom": SpaceZone.PRIVATE,
    "guest_bedroom": SpaceZone.PRIVATE,
    "children_bedroom": SpaceZone.PRIVATE,
    "study": SpaceZone.PRIVATE,
    "home_office": SpaceZone.PRIVATE,
    "dressing": SpaceZone.PRIVATE,
    "kitchen": SpaceZone.SERVICE,
    "utility": SpaceZone.SERVICE,
    "pantry": SpaceZone.SERVICE,
    "store": SpaceZone.SERVICE,
    "attached_toilet": SpaceZone.SERVICE,
    "common_toilet": SpaceZone.SERVICE,
    "powder_room": SpaceZone.SERVICE,
    "bath": SpaceZone.SERVICE,
    "laundry": SpaceZone.SERVICE,
    "servant_room": SpaceZone.SERVICE,
    "servant_toilet": SpaceZone.SERVICE,
    "parking": SpaceZone.OUTDOOR,
    "garage": SpaceZone.OUTDOOR,
    "balcony": SpaceZone.OUTDOOR,
    "terrace": SpaceZone.OUTDOOR,
    "courtyard": SpaceZone.OUTDOOR,
    "puja": SpaceZone.SEMI_PRIVATE,
}


def _priority(room_type: str) -> tuple[int, int, int, int]:
    if room_type in {"bedroom", "master_bedroom", "parents_bedroom"}:
        return (90, 70, 75, 85)
    if room_type in {"living", "drawing", "family_lounge"}:
        return (45, 90, 85, 90)
    if room_type == "kitchen":
        return (55, 75, 95, 90)
    if room_type in {"common_toilet", "attached_toilet", "bath", "powder_room"}:
        return (85, 50, 95, 80)
    if room_type == "dining":
        return (50, 70, 70, 85)
    if room_type == "puja":
        return (75, 65, 65, 80)
    return (50, 60, 60, 65)


def _present_room_types(request: ArchitecturalReasoningInput) -> tuple[str, ...]:
    result: list[str] = []
    for room in request.confirmed.rooms:
        room_type = normalize_room_type(room.room_type)
        if room_type not in result:
            result.append(room_type)

    bedroom_types = {
        "bedroom",
        "master_bedroom",
        "parents_bedroom",
        "guest_bedroom",
        "children_bedroom",
    }
    explicit_bedrooms = sum(
        room.quantity
        for room in request.confirmed.rooms
        if normalize_room_type(room.room_type) in bedroom_types
    )
    if request.confirmed.bedroom_count > explicit_bedrooms and "bedroom" not in result:
        result.append("bedroom")

    parking_types = {"parking", "garage"}
    explicit_parking = sum(
        room.quantity
        for room in request.confirmed.rooms
        if normalize_room_type(room.room_type) in parking_types
    )
    if request.confirmed.parking_count > explicit_parking and "parking" not in result:
        result.append("parking")
    return tuple(result)


def _relationship(
    present: set[str],
    source: str,
    target: str,
    kind: RelationshipKind,
    weight: int,
    rationale: str,
) -> RelationshipIntent | None:
    if source not in present or target not in present:
        return None
    if kind is RelationshipKind.DIRECT_ACCESS:
        return RelationshipIntent(
            source_room_type=source,
            target_room_type=target,
            kind=kind,
            weight=weight,
            max_gap_mm=100,
            min_shared_length_mm=900,
            rationale=rationale,
        )
    if kind is RelationshipKind.ADJACENT:
        return RelationshipIntent(
            source_room_type=source,
            target_room_type=target,
            kind=kind,
            weight=weight,
            max_gap_mm=300,
            min_shared_length_mm=600,
            rationale=rationale,
        )
    if kind is RelationshipKind.NEAR:
        return RelationshipIntent(
            source_room_type=source,
            target_room_type=target,
            kind=kind,
            weight=weight,
            max_gap_mm=1500,
            min_shared_length_mm=0,
            rationale=rationale,
        )
    return RelationshipIntent(
        source_room_type=source,
        target_room_type=target,
        kind=kind,
        weight=weight,
        rationale=rationale,
    )


class FixtureArchitecturalIntelligenceProvider:
    """Deterministic offline reasoning for tests and local development."""

    name = "fixture"

    def reason(
        self,
        request: ArchitecturalReasoningInput,
    ) -> ArchitecturalDesignIntent:
        room_types = _present_room_types(request)
        present = set(room_types)
        lowered_prompt = request.original_prompt.lower()
        wardrobe_requested = "wardrobe" in lowered_prompt

        room_intents: list[RoomArchitecturalIntent] = []
        bedroom_types = {
            "bedroom",
            "master_bedroom",
            "parents_bedroom",
            "guest_bedroom",
            "children_bedroom",
        }

        for room_type in room_types:
            privacy, daylight, ventilation, user = _priority(room_type)
            features: list[RoomFeatureIntent] = []
            if wardrobe_requested and room_type in bedroom_types:
                features.append(
                    RoomFeatureIntent(
                        kind=FeatureKind.WARDROBE_WALL,
                        preferred_depth_mm=600,
                        preferred_wall_length_mm=1800,
                        rationale=(
                            "Client explicitly requested wardrobe space; capture "
                            "the feature without inventing authoritative geometry."
                        ),
                    )
                )
            if room_type in {"living", "bedroom", "master_bedroom", "children_bedroom"}:
                features.append(
                    RoomFeatureIntent(
                        kind=FeatureKind.DAYLIGHT,
                        rationale="Habitable rooms benefit from strong natural daylight.",
                    )
                )

            room_intents.append(
                RoomArchitecturalIntent(
                    room_type=room_type,
                    zone=_ZONE_BY_TYPE.get(room_type, SpaceZone.SEMI_PRIVATE),
                    privacy_priority=privacy,
                    daylight_priority=daylight,
                    ventilation_priority=ventilation,
                    user_priority=user,
                    features=tuple(features),
                    rationale=(
                        "Conventional functional residential zoning only; "
                        "no Vastu rule is encoded in Phase 26A."
                    ),
                )
            )

        relationships: list[RelationshipIntent] = []
        candidates = (
            _relationship(
                present,
                "living",
                "dining",
                RelationshipKind.ADJACENT,
                95,
                "Living and dining should form a coherent public-day zone.",
            ),
            _relationship(
                present,
                "dining",
                "kitchen",
                RelationshipKind.DIRECT_ACCESS,
                95,
                "Kitchen-to-dining movement should be short and direct.",
            ),
            _relationship(
                present,
                "living",
                "common_toilet",
                RelationshipKind.SEPARATE,
                85,
                "Avoid making the common toilet dominant in the living zone.",
            ),
            _relationship(
                present,
                "parking",
                "living",
                RelationshipKind.NEAR,
                60,
                "Parking should have practical access to the house.",
            ),
        )
        relationships.extend(item for item in candidates if item is not None)

        entry_types = tuple(
            item for item in ("foyer", "living", "drawing", "verandah") if item in present
        )
        avoid_views = tuple(
            item
            for item in ("common_toilet", "attached_toilet", "servant_toilet")
            if item in present
        )

        return ArchitecturalDesignIntent(
            project_id=request.confirmed.project_id,
            draft_id=request.confirmed.draft_id,
            provider=self.name,
            model=None,
            strategy_summary=(
                "Prioritize functional zoning, short public/service circulation, "
                "bedroom privacy, daylight/ventilation priorities, and explicit "
                "client features. Vastu weighting is deferred to Phase 26B."
            ),
            room_intents=tuple(room_intents),
            relationships=tuple(relationships),
            circulation=CirculationIntent(
                preferred_entry_room_types=entry_types,
                avoid_direct_view_to_room_types=avoid_views,
                minimize_dead_end_corridors=True,
                minimize_internal_travel=True,
                notes=(
                    "Circulation intent is advisory; exact access remains "
                    "deterministically validated.",
                ),
            ),
            planning_notes=(
                "All generated architectural preferences remain soft.",
                "Hard geometry and validation remain deterministic.",
            ),
        ).with_content_hash()
