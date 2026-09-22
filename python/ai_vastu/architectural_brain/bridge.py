from __future__ import annotations

from ai_vastu.plan_schema import (
    AdjacencyPreference,
    AdjacencyProhibition,
    RoomType,
)
from ai_vastu.requirements.generation_adapter import (
    CompiledGeneration,
)

from .models import ArchitecturalConcept


def _room_type(
    value: str,
) -> RoomType | None:
    normalized = value.strip().lower().replace(" ", "_")

    aliases = {
        "toilet": "common_toilet",
        "bathroom": "common_toilet",
        "car_parking": "parking",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    try:
        return RoomType(normalized)
    except ValueError:
        return None


def apply_architectural_concept(
    compiled: CompiledGeneration,
    concept: ArchitecturalConcept,
) -> CompiledGeneration:
    """Apply late architectural concept intent without violating authority.

    Earlier confirmed/user/architectural constraints always win. Concept
    topology may strengthen the solver objective but cannot reverse an
    established adjacency prohibition or preference.
    """

    concept_rooms = {
        mapped: item for item in concept.rooms if (mapped := _room_type(item.room_type)) is not None
    }

    updated = []
    notices = list(compiled.notices)

    skipped_conflicts = 0
    applied_topology = 0
    ignored_hard_size_caps = 0

    for requirement in compiled.request.room_requirements:
        changes: dict[
            str,
            object,
        ] = {}

        room = concept_rooms.get(requirement.room_type)

        if room is not None:
            if room.target_area_mm2 is not None:
                target = max(
                    requirement.min_area_mm2,
                    room.target_area_mm2,
                )
                if requirement.max_area_mm2 is not None:
                    target = min(
                        target,
                        requirement.max_area_mm2,
                    )
                changes["preferred_area_mm2"] = target

            if room.target_width_mm is not None:
                target = max(
                    requirement.min_width_mm,
                    room.target_width_mm,
                )
                if requirement.max_width_mm is not None:
                    target = min(
                        target,
                        requirement.max_width_mm,
                    )
                changes["preferred_width_mm"] = target

            if room.target_depth_mm is not None:
                target = max(
                    requirement.min_depth_mm,
                    room.target_depth_mm,
                )
                if requirement.max_depth_mm is not None:
                    target = min(
                        target,
                        requirement.max_depth_mm,
                    )
                changes["preferred_depth_mm"] = target

            # Concept sizing is lower-authority AI intent. A concept maximum
            # must not become a new hard feasibility cap: on compact sites it
            # can conflict with the deterministic residential occupancy floor
            # and reject an otherwise valid confirmed program. Preserve any
            # earlier authoritative maximum already carried by the requirement
            # and express the concept only through preferred dimensions/area.
            if room.max_area_mm2 is not None:
                ignored_hard_size_caps += 1

        preferences = list(requirement.adjacency_preferences)
        prohibitions = list(requirement.adjacency_prohibitions)

        preferred_targets = {item.target_room_type for item in preferences}
        prohibited_targets = {item.target_room_type for item in prohibitions}

        for edge in concept.topology:
            source = _room_type(edge.source_room_type)
            related_room_type = _room_type(edge.target_room_type)

            if (
                source != requirement.room_type
                or related_room_type is None
                or related_room_type == requirement.room_type
            ):
                continue

            # Road access is a site/boundary contract, not a room-to-room
            # adjacency. Deterministic residential planning already owns it.
            if edge.relation == "ROAD_ACCESS":
                continue

            if edge.relation in {
                "DOOR",
                "ADJACENT",
                "NEAR",
            }:
                if (
                    related_room_type in prohibited_targets
                    or related_room_type in preferred_targets
                ):
                    skipped_conflicts += 1
                    continue

                if edge.relation == "DOOR":
                    max_gap_mm = 0
                    min_shared_length_mm = 800
                elif edge.relation == "ADJACENT":
                    max_gap_mm = 0
                    min_shared_length_mm = 0
                else:
                    max_gap_mm = 1_200
                    min_shared_length_mm = None

                preferences.append(
                    AdjacencyPreference(
                        target_room_type=related_room_type,
                        weight=edge.weight,
                        max_gap_mm=max_gap_mm,
                        min_shared_length_mm=min_shared_length_mm,
                    )
                )
                preferred_targets.add(related_room_type)
                applied_topology += 1

            elif edge.relation == "AVOID":
                if (
                    related_room_type in preferred_targets
                    or related_room_type in prohibited_targets
                ):
                    skipped_conflicts += 1
                    continue

                prohibitions.append(
                    AdjacencyProhibition(
                        target_room_type=related_room_type,
                        hard=False,
                    )
                )
                prohibited_targets.add(related_room_type)
                applied_topology += 1

        changes["adjacency_preferences"] = tuple(preferences)
        changes["adjacency_prohibitions"] = tuple(prohibitions)

        updated.append(requirement.model_copy(update=changes))

    topology_pairs = tuple(
        sorted(
            (
                min(
                    edge.source_room_type,
                    edge.target_room_type,
                ),
                max(
                    edge.source_room_type,
                    edge.target_room_type,
                ),
                edge.relation,
                edge.weight,
            )
            for edge in concept.topology
        )
    )

    notices.append(
        "Architectural Brain candidate topology applied as "
        "non-geometric solver intent; "
        f"concept_id={concept.concept_id}; "
        f"precedent_ids={','.join(concept.precedent_ids) or 'none'}; "
        f"applied_edges={applied_topology}; "
        f"authority_conflicts_skipped={skipped_conflicts}; "
        f"non_authoritative_hard_size_caps_ignored={ignored_hard_size_caps}; "
        f"topology={topology_pairs}; "
        "authoritative_geometry=false."
    )

    request = compiled.request.model_copy(update={"room_requirements": tuple(updated)})
    updated_by_id = {item.id: item for item in updated}
    floor_requirements = tuple(
        tuple(updated_by_id.get(item.id, item) for item in floor)
        for floor in compiled.request.floor_requirements
    )
    request = request.model_copy(update={"floor_requirements": floor_requirements})

    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=tuple(notices),
    )
