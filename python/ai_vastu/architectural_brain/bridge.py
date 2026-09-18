from __future__ import annotations

from ai_vastu.plan_schema import AdjacencyPreference, AdjacencyProhibition, RoomType
from ai_vastu.requirements.generation_adapter import CompiledGeneration

from .models import ArchitecturalConcept


def _room_type(value: str) -> RoomType | None:
    normalized = value.strip().lower().replace(" ", "_")
    aliases = {"toilet": "common_toilet", "bathroom": "common_toilet", "car_parking": "parking"}
    normalized = aliases.get(normalized, normalized)
    try:
        return RoomType(normalized)
    except ValueError:
        return None


def apply_architectural_concept(
    compiled: CompiledGeneration,
    concept: ArchitecturalConcept,
) -> CompiledGeneration:
    concept_rooms = {
        _room_type(item.room_type): item
        for item in concept.rooms
        if _room_type(item.room_type) is not None
    }
    updated = []
    notices = list(compiled.notices)

    for requirement in compiled.request.room_requirements:
        changes: dict[str, object] = {}
        room = concept_rooms.get(requirement.room_type)
        if room is not None:
            if room.target_area_mm2 is not None:
                target = max(requirement.min_area_mm2, room.target_area_mm2)
                if requirement.max_area_mm2 is not None:
                    target = min(target, requirement.max_area_mm2)
                changes["preferred_area_mm2"] = target
            if room.target_width_mm is not None:
                target = max(requirement.min_width_mm, room.target_width_mm)
                if requirement.max_width_mm is not None:
                    target = min(target, requirement.max_width_mm)
                changes["preferred_width_mm"] = target
            if room.target_depth_mm is not None:
                target = max(requirement.min_depth_mm, room.target_depth_mm)
                if requirement.max_depth_mm is not None:
                    target = min(target, requirement.max_depth_mm)
                changes["preferred_depth_mm"] = target
            if room.max_area_mm2 is not None:
                maximum = room.max_area_mm2
                if requirement.max_area_mm2 is not None:
                    maximum = min(maximum, requirement.max_area_mm2)
                changes["max_area_mm2"] = maximum

        preferences = list(requirement.adjacency_preferences)
        prohibitions = list(requirement.adjacency_prohibitions)
        for edge in concept.topology:
            source = _room_type(edge.source_room_type)
            target_room_type = _room_type(edge.target_room_type)
            if source != requirement.room_type or target_room_type is None:
                continue
            if edge.relation in {"DOOR", "ADJACENT", "NEAR", "ROAD_ACCESS"}:
                preferences.append(
                    AdjacencyPreference(
                        target_room_type=target_room_type,
                        weight=edge.weight,
                        max_gap_mm=0 if edge.relation in {"DOOR", "ADJACENT"} else 1200,
                        min_shared_length_mm=800 if edge.relation == "DOOR" else 0,
                    )
                )
            elif edge.relation == "AVOID":
                prohibitions.append(
                    AdjacencyProhibition(target_room_type=target_room_type, hard=False)
                )
        changes["adjacency_preferences"] = tuple(preferences)
        changes["adjacency_prohibitions"] = tuple(prohibitions)
        updated.append(requirement.model_copy(update=changes))

    notices.append(
        "Phase 26 architectural-brain concept applied as soft planning preferences only; "
        f"concept_id={concept.concept_id}; authoritative_geometry=false."
    )
    request = compiled.request.model_copy(update={"room_requirements": tuple(updated)})
    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=tuple(notices),
    )
