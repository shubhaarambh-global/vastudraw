from __future__ import annotations

from uuid import UUID

from .models import ArchitecturalConcept, ConceptRoom, RetrievedPrecedent, TopologyEdge

_ROOM_TARGETS: dict[str, tuple[int, int, int, int | None, str]] = {
    "living": (18_500_000, 3_300, 4_200, 30_000_000, "PUBLIC"),
    "dining": (9_500_000, 2_700, 3_000, 16_000_000, "PUBLIC"),
    "kitchen": (9_000_000, 2_400, 3_000, 15_000_000, "SERVICE"),
    "bedroom": (12_000_000, 3_000, 3_300, 18_000_000, "PRIVATE"),
    "master_bedroom": (14_000_000, 3_300, 3_600, 22_000_000, "PRIVATE"),
    "common_toilet": (3_600_000, 1_500, 2_100, 5_500_000, "SERVICE"),
    "attached_toilet": (3_600_000, 1_500, 2_100, 5_500_000, "SERVICE"),
    "puja": (2_200_000, 1_200, 1_500, 4_000_000, "SACRED"),
    "lobby": (4_500_000, 1_200, 2_400, 8_000_000, "SEMI_PRIVATE"),
    "parking": (15_000_000, 2_700, 5_000, 18_000_000, "VEHICLE"),
    "garage": (15_000_000, 2_700, 5_000, 18_000_000, "VEHICLE"),
    "utility": (4_500_000, 1_500, 2_400, 7_000_000, "SERVICE"),
    "store": (3_000_000, 1_500, 1_800, 5_000_000, "SERVICE"),
}


def _concept_room(room_type: str) -> ConceptRoom:
    target = _ROOM_TARGETS.get(room_type)
    if target is None:
        return ConceptRoom(room_type=room_type, zone="SEMI_PRIVATE")
    area, width, depth, max_area, zone = target
    return ConceptRoom(
        room_type=room_type,
        zone=zone,  # type: ignore[arg-type]
        target_area_mm2=area,
        target_width_mm=width,
        target_depth_mm=depth,
        max_area_mm2=max_area,
        prefer_external_wall=room_type
        in {"living", "bedroom", "master_bedroom", "kitchen", "utility"},
    )


def default_residential_topology(room_types: tuple[str, ...]) -> tuple[TopologyEdge, ...]:
    present = set(room_types)
    edges: list[TopologyEdge] = []

    def add(source: str, target: str, relation: str, weight: int) -> None:
        if source in present and target in present:
            edges.append(
                TopologyEdge(
                    source_room_type=source,
                    target_room_type=target,
                    relation=relation,  # type: ignore[arg-type]
                    weight=weight,
                )
            )

    add("living", "dining", "DOOR", 95)
    add("dining", "kitchen", "DOOR", 95)
    add("living", "kitchen", "NEAR", 65)
    add("living", "lobby", "DOOR", 100)
    add("lobby", "bedroom", "DOOR", 100)
    add("lobby", "master_bedroom", "DOOR", 100)
    add("lobby", "common_toilet", "DOOR", 80)
    add("living", "common_toilet", "AVOID", 95)
    add("dining", "common_toilet", "AVOID", 95)
    add("parking", "living", "NEAR", 70)
    add("garage", "living", "NEAR", 70)
    add("puja", "living", "NEAR", 75)
    add("puja", "dining", "NEAR", 55)
    return tuple(edges)


def build_fallback_concept(
    *,
    project_id: UUID,
    room_types: tuple[str, ...],
    precedents: tuple[RetrievedPrecedent, ...] = (),
    ordinal: int = 0,
) -> ArchitecturalConcept:
    unique = tuple(dict.fromkeys(room_types))
    precedent_ids = tuple(item.fingerprint.precedent_id for item in precedents[:8])
    return ArchitecturalConcept(
        project_id=project_id,
        concept_id=f"fallback-{ordinal}",
        title=f"Residential topology {ordinal + 1}",
        rooms=tuple(_concept_room(item) for item in unique),
        topology=default_residential_topology(unique),
        precedent_ids=precedent_ids,
        design_rationale=(
            "Public rooms form the arrival/social zone.",
            "Bedrooms are connected through a semi-private circulation layer.",
            "Kitchen/service spaces remain logically connected to dining/living.",
            "Parking is dimension-capped and never used as filler area.",
            "Unbuilt portions of the confirmed envelope must be purposefully classified.",
        ),
    ).with_content_hash()
