from __future__ import annotations

from collections import Counter
from uuid import UUID, uuid5

from ai_vastu.geometry.ring_math import area2_polygon
from ai_vastu.plan_schema.models import AdjacencyPreference, RoomRequirement, RoomType

from .errors import ConstraintConflictError, ConstraintInfeasibleError
from .models import (
    AdjacencyAvoidanceObjective,
    AdjacencyPreferenceObjective,
    AdjacencyProhibitionConstraint,
    AspectRatioConstraint,
    AvailableFloorsConstraint,
    CompiledConstraintProblem,
    CompilerNotice,
    ConstraintCompilerInput,
    ConstraintNoticeSeverity,
    ConstraintOrigin,
    ContainmentConstraint,
    DimensionAxis,
    FloorPreferenceObjective,
    HardConstraint,
    MaximumAreaConstraint,
    MaximumDimensionConstraint,
    MinimumAreaConstraint,
    MinimumDimensionConstraint,
    PreferredAreaObjective,
    PreferredDimensionObjective,
    RoomInstance,
    RoomPrioritiesObjective,
    SoftConstraint,
)

_ROOM_INSTANCE_NAMESPACE = UUID("1cf9b0e5-669f-54f4-a050-d91877d7cd0a")
_CONSTRAINT_NAMESPACE = UUID("0b91840f-a154-55db-af12-cbc1a8f41bf1")

_PUJA_SANITARY_PROHIBITIONS = frozenset(
    {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
)


def _stable_id(*parts: object) -> UUID:
    return uuid5(_CONSTRAINT_NAMESPACE, "|".join(str(part) for part in parts))


def _room_instance_id(
    requirement_id: UUID,
    ordinal: int,
    instance_namespace: str,
) -> UUID:
    return uuid5(
        _ROOM_INSTANCE_NAMESPACE,
        f"{instance_namespace}|{requirement_id}|{ordinal}",
    )


def _target_available(
    source: RoomRequirement,
    target: RoomType,
    counts: Counter[RoomType],
) -> bool:
    count = counts[target]
    if target == source.room_type:
        return count >= 2
    return count >= 1


def _validate_requirement(
    requirement: RoomRequirement,
    available_floors: set[int],
    room_type_counts: Counter[RoomType],
) -> None:
    unknown_floors = set(requirement.floor_preference) - available_floors
    if unknown_floors:
        ordered = ", ".join(str(value) for value in sorted(unknown_floors))
        raise ConstraintConflictError(
            f"RoomRequirement {requirement.id} prefers unavailable floor(s): {ordered}."
        )

    preference_targets = [item.target_room_type for item in requirement.adjacency_preferences]
    prohibition_targets = [item.target_room_type for item in requirement.adjacency_prohibitions]
    if len(preference_targets) != len(set(preference_targets)):
        raise ConstraintConflictError(
            f"RoomRequirement {requirement.id} has duplicate adjacency preferences."
        )
    if len(prohibition_targets) != len(set(prohibition_targets)):
        raise ConstraintConflictError(
            f"RoomRequirement {requirement.id} has duplicate adjacency prohibitions."
        )
    conflicting_targets = set(preference_targets) & set(prohibition_targets)
    if conflicting_targets:
        names = ", ".join(sorted(target.value for target in conflicting_targets))
        raise ConstraintConflictError(
            f"RoomRequirement {requirement.id} both prefers and prohibits adjacency to: {names}."
        )

    if requirement.max_area_mm2 is not None:
        minimum_rectangle_area = requirement.min_width_mm * requirement.min_depth_mm
        if minimum_rectangle_area > requirement.max_area_mm2:
            raise ConstraintInfeasibleError(
                f"RoomRequirement {requirement.id} minimum width/depth already exceed max area."
            )
    if requirement.max_width_mm is not None and requirement.max_depth_mm is not None:
        maximum_rectangle_area = requirement.max_width_mm * requirement.max_depth_mm
        if maximum_rectangle_area < requirement.min_area_mm2:
            raise ConstraintInfeasibleError(
                f"RoomRequirement {requirement.id} maximum width/depth cannot reach min area."
            )

    for preference in requirement.adjacency_preferences:
        if not _target_available(requirement, preference.target_room_type, room_type_counts):
            raise ConstraintConflictError(
                f"RoomRequirement {requirement.id} prefers adjacency to unavailable room type "
                f"{preference.target_room_type.value}."
            )


def _append_dimension_constraints(
    hard: list[HardConstraint],
    soft: list[SoftConstraint],
    instance: RoomInstance,
    requirement: RoomRequirement,
) -> None:
    for axis, minimum, preferred, maximum in (
        (
            DimensionAxis.WIDTH,
            requirement.min_width_mm,
            requirement.preferred_width_mm,
            requirement.max_width_mm,
        ),
        (
            DimensionAxis.DEPTH,
            requirement.min_depth_mm,
            requirement.preferred_depth_mm,
            requirement.max_depth_mm,
        ),
    ):
        hard.append(
            MinimumDimensionConstraint(
                id=_stable_id(instance.id, "min-dimension", axis.value, minimum),
                room_instance_id=instance.id,
                axis=axis,
                minimum_mm=minimum,
            )
        )
        if maximum is not None:
            hard.append(
                MaximumDimensionConstraint(
                    id=_stable_id(instance.id, "max-dimension", axis.value, maximum),
                    room_instance_id=instance.id,
                    axis=axis,
                    maximum_mm=maximum,
                )
            )
        if preferred is not None:
            soft.append(
                PreferredDimensionObjective(
                    id=_stable_id(instance.id, "preferred-dimension", axis.value, preferred),
                    room_instance_id=instance.id,
                    axis=axis,
                    preferred_mm=preferred,
                    weight=requirement.user_priority,
                )
            )


def _append_area_constraints(
    hard: list[HardConstraint],
    soft: list[SoftConstraint],
    instance: RoomInstance,
    requirement: RoomRequirement,
) -> None:
    hard.append(
        MinimumAreaConstraint(
            id=_stable_id(instance.id, "min-area", requirement.min_area_mm2),
            room_instance_id=instance.id,
            minimum_area_mm2=requirement.min_area_mm2,
        )
    )
    if requirement.max_area_mm2 is not None:
        hard.append(
            MaximumAreaConstraint(
                id=_stable_id(instance.id, "max-area", requirement.max_area_mm2),
                room_instance_id=instance.id,
                maximum_area_mm2=requirement.max_area_mm2,
            )
        )
    if requirement.preferred_area_mm2 is not None:
        soft.append(
            PreferredAreaObjective(
                id=_stable_id(instance.id, "preferred-area", requirement.preferred_area_mm2),
                room_instance_id=instance.id,
                preferred_area_mm2=requirement.preferred_area_mm2,
                weight=requirement.user_priority,
            )
        )


def _append_adjacency_constraints(
    hard: list[HardConstraint],
    soft: list[SoftConstraint],
    notices: list[CompilerNotice],
    instance: RoomInstance,
    requirement: RoomRequirement,
    room_type_counts: Counter[RoomType],
) -> None:
    for preference in requirement.adjacency_preferences:
        _append_adjacency_preference(soft, instance, preference)

    for prohibition in requirement.adjacency_prohibitions:
        if not _target_available(requirement, prohibition.target_room_type, room_type_counts):
            notices.append(
                CompilerNotice(
                    code="VACUOUS_ADJACENCY_PROHIBITION",
                    severity=ConstraintNoticeSeverity.INFO,
                    requirement_id=requirement.id,
                    message=(
                        "Adjacency prohibition has no possible target in this requirement set: "
                        f"{prohibition.target_room_type.value}."
                    ),
                )
            )
            continue
        if prohibition.hard:
            hard.append(
                AdjacencyProhibitionConstraint(
                    id=_stable_id(
                        instance.id,
                        "adjacency-prohibition",
                        prohibition.target_room_type.value,
                    ),
                    room_instance_id=instance.id,
                    target_room_type=prohibition.target_room_type,
                )
            )
        else:
            soft.append(
                AdjacencyAvoidanceObjective(
                    id=_stable_id(
                        instance.id,
                        "adjacency-avoidance",
                        prohibition.target_room_type.value,
                    ),
                    room_instance_id=instance.id,
                    target_room_type=prohibition.target_room_type,
                )
            )


def _append_adjacency_preference(
    soft: list[SoftConstraint],
    instance: RoomInstance,
    preference: AdjacencyPreference,
) -> None:
    soft.append(
        AdjacencyPreferenceObjective(
            id=_stable_id(
                instance.id,
                "adjacency-preference",
                preference.target_room_type.value,
                preference.weight,
                preference.max_gap_mm,
                preference.min_shared_length_mm,
            ),
            room_instance_id=instance.id,
            target_room_type=preference.target_room_type,
            weight=preference.weight,
            max_gap_mm=preference.max_gap_mm,
            min_shared_length_mm=preference.min_shared_length_mm,
        )
    )


def _append_architectural_invariants(
    hard: list[HardConstraint],
    instances: list[RoomInstance],
) -> None:
    """Add deterministic, product-approved residential safety/quality invariants.

    These constraints are not model-authored judgement and are not Vastu scoring
    rules. They are explicit architectural invariants enforced before geometry
    can be accepted.
    """

    present_types = {room.room_type for room in instances}

    sanitary_types = tuple(
        sorted(
            _PUJA_SANITARY_PROHIBITIONS & present_types,
            key=lambda item: item.value,
        )
    )

    if not sanitary_types:
        return

    puja_rooms = tuple(
        sorted(
            (room for room in instances if room.room_type is RoomType.PUJA),
            key=lambda item: str(item.id),
        )
    )

    for puja in puja_rooms:
        for sanitary_type in sanitary_types:
            hard.append(
                AdjacencyProhibitionConstraint(
                    id=_stable_id(
                        puja.id,
                        "architectural-invariant",
                        "puja-sanitary-separation",
                        sanitary_type.value,
                    ),
                    origin=ConstraintOrigin.ARCHITECTURAL_INVARIANT,
                    room_instance_id=puja.id,
                    target_room_type=sanitary_type,
                )
            )


def _preflight_total_area(input_data: ConstraintCompilerInput) -> None:
    buildable_area2 = area2_polygon(input_data.buildable_area.polygon)
    if buildable_area2 <= 0:
        raise ConstraintInfeasibleError("Buildable area must have positive exact area.")
    total_capacity_area2 = buildable_area2 * len(input_data.available_floor_indices)
    required_area2 = sum(
        requirement.min_area_mm2 * requirement.quantity * 2
        for requirement in input_data.room_requirements
    )
    if required_area2 > total_capacity_area2:
        raise ConstraintInfeasibleError(
            "Total minimum room area exceeds total buildable floor capacity."
        )


def compile_constraints(input_data: ConstraintCompilerInput) -> CompiledConstraintProblem:
    """Compile verified room requirements into deterministic solver-agnostic constraints.

    Phase 6 does not apply hidden architectural defaults and does not invoke a solver.
    Every assumption in the output must already be explicit in ``input_data.assumptions``.
    """

    available_floors = set(input_data.available_floor_indices)
    room_type_counts: Counter[RoomType] = Counter()
    for requirement in input_data.room_requirements:
        room_type_counts[requirement.room_type] += requirement.quantity

    for requirement in input_data.room_requirements:
        _validate_requirement(requirement, available_floors, room_type_counts)
    _preflight_total_area(input_data)

    instances: list[RoomInstance] = []
    hard: list[HardConstraint] = []
    soft: list[SoftConstraint] = []
    notices: list[CompilerNotice] = []
    floors = tuple(sorted(input_data.available_floor_indices))

    for requirement in sorted(input_data.room_requirements, key=lambda item: str(item.id)):
        for ordinal in range(1, requirement.quantity + 1):
            instance = RoomInstance(
                id=_room_instance_id(
                    requirement.id,
                    ordinal,
                    input_data.instance_namespace,
                ),
                requirement_id=requirement.id,
                ordinal=ordinal,
                room_type=requirement.room_type,
                locked=requirement.locked,
                vastu_profile_refs=tuple(sorted(requirement.vastu_profile_refs)),
            )
            instances.append(instance)
            hard.append(
                ContainmentConstraint(
                    id=_stable_id(instance.id, "containment"),
                    room_instance_id=instance.id,
                )
            )
            hard.append(
                AvailableFloorsConstraint(
                    id=_stable_id(instance.id, "available-floors", *floors),
                    room_instance_id=instance.id,
                    allowed_floor_indices=floors,
                )
            )
            _append_dimension_constraints(hard, soft, instance, requirement)
            _append_area_constraints(hard, soft, instance, requirement)
            if requirement.aspect_ratio is not None:
                hard.append(
                    AspectRatioConstraint(
                        id=_stable_id(
                            instance.id,
                            "aspect-ratio",
                            requirement.aspect_ratio.min_ratio_milli,
                            requirement.aspect_ratio.max_ratio_milli,
                        ),
                        room_instance_id=instance.id,
                        min_ratio_milli=requirement.aspect_ratio.min_ratio_milli,
                        max_ratio_milli=requirement.aspect_ratio.max_ratio_milli,
                    )
                )
            if requirement.floor_preference:
                soft.append(
                    FloorPreferenceObjective(
                        id=_stable_id(
                            instance.id,
                            "floor-preference",
                            *sorted(requirement.floor_preference),
                        ),
                        room_instance_id=instance.id,
                        preferred_floor_indices=tuple(sorted(requirement.floor_preference)),
                        weight=requirement.user_priority,
                    )
                )
            _append_adjacency_constraints(
                hard,
                soft,
                notices,
                instance,
                requirement,
                room_type_counts,
            )
            soft.append(
                RoomPrioritiesObjective(
                    id=_stable_id(
                        instance.id,
                        "priorities",
                        requirement.privacy_priority,
                        requirement.daylight_priority,
                        requirement.ventilation_priority,
                        requirement.user_priority,
                    ),
                    room_instance_id=instance.id,
                    privacy_priority=requirement.privacy_priority,
                    daylight_priority=requirement.daylight_priority,
                    ventilation_priority=requirement.ventilation_priority,
                    user_priority=requirement.user_priority,
                )
            )

    _append_architectural_invariants(
        hard,
        instances,
    )

    problem = CompiledConstraintProblem(
        buildable_area=input_data.buildable_area,
        available_floor_indices=floors,
        room_instances=tuple(sorted(instances, key=lambda item: str(item.id))),
        hard_constraints=tuple(sorted(hard, key=lambda item: str(item.id))),
        soft_constraints=tuple(sorted(soft, key=lambda item: str(item.id))),
        assumptions=tuple(sorted(input_data.assumptions, key=lambda item: str(item.id))),
        notices=tuple(
            sorted(
                notices,
                key=lambda item: (
                    item.code,
                    "" if item.requirement_id is None else str(item.requirement_id),
                    item.message,
                ),
            )
        ),
    )
    return problem.with_content_hash()
