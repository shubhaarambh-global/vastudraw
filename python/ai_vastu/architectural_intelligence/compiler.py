from __future__ import annotations

from ai_vastu.plan_schema import (
    AdjacencyPreference,
    AdjacencyProhibition,
    RoomRequirement,
    RoomType,
)
from ai_vastu.requirements.generation_adapter import CompiledGeneration
from ai_vastu.requirements.generation_profile import normalize_room_type

from .models import ArchitecturalDesignIntent, RelationshipKind


def _known_room_type(value: str) -> RoomType | None:
    normalized = normalize_room_type(value)
    try:
        return RoomType(normalized)
    except ValueError:
        return None


def _relationship_defaults(
    kind: RelationshipKind,
) -> tuple[int | None, int | None]:
    if kind is RelationshipKind.DIRECT_ACCESS:
        return (100, 900)
    if kind is RelationshipKind.ADJACENT:
        return (300, 600)
    if kind is RelationshipKind.NEAR:
        return (1500, 0)
    return (None, None)


def apply_design_intent(
    compiled: CompiledGeneration,
    intent: ArchitecturalDesignIntent,
) -> CompiledGeneration:
    """Apply Phase 26A as soft preferences only.

    This function never turns model-authored architectural judgement into a
    hard dimensional, containment, safety, or Vastu constraint.
    """

    requirements = list(compiled.request.room_requirements)
    present_counts: dict[RoomType, int] = {}
    for requirement in requirements:
        present_counts[requirement.room_type] = (
            present_counts.get(requirement.room_type, 0) + requirement.quantity
        )

    room_intents = {normalize_room_type(item.room_type): item for item in intent.room_intents}
    notices = list(compiled.notices)
    updated: list[RoomRequirement] = []

    for requirement in requirements:
        room_type = requirement.room_type.value
        room_intent = room_intents.get(room_type)
        changes: dict[str, object] = {}

        if room_intent is not None:
            changes.update(
                {
                    "privacy_priority": room_intent.privacy_priority,
                    "daylight_priority": room_intent.daylight_priority,
                    "ventilation_priority": room_intent.ventilation_priority,
                    "user_priority": room_intent.user_priority,
                }
            )
            if (
                room_intent.preferred_width_mm is not None
                and room_intent.preferred_width_mm >= requirement.min_width_mm
            ):
                changes["preferred_width_mm"] = room_intent.preferred_width_mm
            elif room_intent.preferred_width_mm is not None:
                notices.append(
                    f"26A ignored preferred width below confirmed minimum for {room_type}."
                )

            if (
                room_intent.preferred_depth_mm is not None
                and room_intent.preferred_depth_mm >= requirement.min_depth_mm
            ):
                changes["preferred_depth_mm"] = room_intent.preferred_depth_mm
            elif room_intent.preferred_depth_mm is not None:
                notices.append(
                    f"26A ignored preferred depth below confirmed minimum for {room_type}."
                )

            if (
                room_intent.preferred_area_mm2 is not None
                and room_intent.preferred_area_mm2 >= requirement.min_area_mm2
            ):
                changes["preferred_area_mm2"] = room_intent.preferred_area_mm2
            elif room_intent.preferred_area_mm2 is not None:
                notices.append(
                    f"26A ignored preferred area below confirmed minimum for {room_type}."
                )

            for feature in room_intent.features:
                notices.append(
                    "26A captured feature "
                    f"{feature.kind.value} for {room_type}; exact furniture geometry "
                    "is intentionally not invented in this phase."
                )

        preferences = list(requirement.adjacency_preferences)
        prohibitions = list(requirement.adjacency_prohibitions)
        preference_targets = {item.target_room_type for item in preferences}
        prohibition_targets = {item.target_room_type for item in prohibitions}

        for relationship in intent.relationships:
            if normalize_room_type(relationship.source_room_type) != room_type:
                continue

            target = _known_room_type(relationship.target_room_type)
            if target is None or target not in present_counts:
                notices.append(
                    "26A skipped relationship to unavailable/unsupported room type: "
                    f"{relationship.target_room_type}."
                )
                continue
            if target == requirement.room_type and present_counts[target] < 2:
                notices.append(f"26A skipped self-relationship for single {room_type} requirement.")
                continue

            if relationship.kind is RelationshipKind.SEPARATE:
                if target not in prohibition_targets and target not in preference_targets:
                    prohibitions.append(
                        AdjacencyProhibition(
                            target_room_type=target,
                            hard=False,
                        )
                    )
                    prohibition_targets.add(target)
                continue

            if target in preference_targets or target in prohibition_targets:
                continue

            default_gap, default_shared = _relationship_defaults(relationship.kind)
            preferences.append(
                AdjacencyPreference(
                    target_room_type=target,
                    weight=relationship.weight,
                    max_gap_mm=(
                        relationship.max_gap_mm
                        if relationship.max_gap_mm is not None
                        else default_gap
                    ),
                    min_shared_length_mm=(
                        relationship.min_shared_length_mm
                        if relationship.min_shared_length_mm is not None
                        else default_shared
                    ),
                )
            )
            preference_targets.add(target)

        changes["adjacency_preferences"] = tuple(preferences)
        changes["adjacency_prohibitions"] = tuple(prohibitions)
        updated.append(requirement.model_copy(update=changes))

    intent_hash = intent.content_hash or intent.compute_content_hash()
    notices.append(
        "Phase 26A architectural intelligence applied as soft preferences only; "
        f"intent_hash={intent_hash}; provider={intent.provider}; "
        f"model={intent.model or 'none'}."
    )

    request = compiled.request.model_copy(update={"room_requirements": tuple(updated)})
    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=tuple(notices),
    )
