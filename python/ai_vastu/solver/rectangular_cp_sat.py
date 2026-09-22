from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import Any
from uuid import UUID, uuid5

from ortools.sat.python import cp_model

from ai_vastu.constraints import (
    AdjacencyAvoidanceObjective,
    AdjacencyPreferenceObjective,
    AdjacencyProhibitionConstraint,
    AspectRatioConstraint,
    AvailableFloorsConstraint,
    CompiledConstraintProblem,
    ConstraintOrigin,
    ContainmentConstraint,
    DimensionAxis,
    FloorPreferenceObjective,
    MaximumAreaConstraint,
    MaximumDimensionConstraint,
    MinimumAreaConstraint,
    MinimumDimensionConstraint,
    PreferredAreaObjective,
    PreferredDimensionObjective,
    RoomPrioritiesObjective,
)
from ai_vastu.plan_schema import IntPolygon, RoomType

from .errors import SolverModelError, UnsupportedSolverProblemError
from .models import (
    ObjectiveContribution,
    PlannerBoundarySide,
    PlannerConfig,
    PlannerNotice,
    PlannerNoticeSeverity,
    PlannerResult,
    PlannerSearchVariant,
    PlannerStatus,
    ResidentialPlanningConfig,
    RoomPlacement,
    SolverRunMetadata,
)
from .residential_quality import RoomAreaBasis, allocate_room_area_targets

_SYSTEM_OBJECTIVE_NAMESPACE = UUID("38cf35f1-3f68-52d2-88b5-b455219a54cf")
_AREA_PENALTY_DIVISOR_MM2 = 1_000
_WET_ROOM_TYPES = frozenset(
    {
        RoomType.KITCHEN,
        RoomType.UTILITY,
        RoomType.LAUNDRY,
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
)


_SANITARY_WET_ROOM_TYPES = frozenset(
    {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
)


def _wet_stack_group(room_type: RoomType) -> str:
    return "SANITARY" if room_type in _SANITARY_WET_ROOM_TYPES else "SERVICE"

@dataclass(frozen=True)
class _RectangleBounds:
    min_x_mm: int
    min_y_mm: int
    width_mm: int
    depth_mm: int


@dataclass
class _RoomVars:
    x: Any
    y: Any
    width: Any
    depth: Any
    x_end: Any
    y_end: Any
    area_cells2: Any
    clear_width_mm: Any
    clear_depth_mm: Any
    clear_area_mm2: Any
    x_interval: Any
    y_interval: Any


@dataclass(frozen=True)
class _PenaltyTerm:
    constraint_id: Any
    kind: str
    weight: int
    expression: Any


@dataclass(frozen=True)
class _AdjacencyTargetSpec:
    max_gap_mm: int | None
    min_shared_length_mm: int | None


def _system_objective_id(problem: CompiledConstraintProblem, key: str) -> UUID:
    problem_hash = problem.content_hash or problem.compute_content_hash()
    return uuid5(_SYSTEM_OBJECTIVE_NAMESPACE, f"{problem_hash}|{key}")


def _pin_room_to_boundary(
    model: Any,
    room: _RoomVars,
    *,
    side: PlannerBoundarySide,
    width_cells: int,
    depth_cells: int,
) -> None:
    if side is PlannerBoundarySide.SOUTH:
        model.add(room.y == 0)
    elif side is PlannerBoundarySide.EAST:
        model.add(room.x_end == width_cells)
    elif side is PlannerBoundarySide.NORTH:
        model.add(room.y_end == depth_cells)
    else:
        model.add(room.x == 0)


def _apply_parking_clear_dimension_constraints(
    model: Any,
    room: _RoomVars,
    *,
    side: PlannerBoundarySide,
    planning: ResidentialPlanningConfig,
) -> None:
    """Require a usable parking bay relative to the confirmed road edge.

    Frontage is the clear dimension parallel to the road boundary.
    Depth is the clear dimension extending inward from that boundary.
    These constraints apply to clear usable dimensions after the
    wall/clearance reserve has been deducted.
    """

    if side in {
        PlannerBoundarySide.NORTH,
        PlannerBoundarySide.SOUTH,
    }:
        model.add(room.clear_width_mm >= planning.parking_min_frontage_mm)
        model.add(room.clear_depth_mm >= planning.parking_min_depth_mm)
    else:
        model.add(room.clear_depth_mm >= planning.parking_min_frontage_mm)
        model.add(room.clear_width_mm >= planning.parking_min_depth_mm)


def _scaled_area_penalty(
    model: Any,
    *,
    raw_penalty_mm2: Any,
    upper_mm2: int,
    name: str,
) -> Any:
    upper = upper_mm2 // _AREA_PENALTY_DIVISOR_MM2 + 1
    scaled = model.new_int_var(0, upper, name)
    model.add_division_equality(
        scaled,
        raw_penalty_mm2,
        _AREA_PENALTY_DIVISOR_MM2,
    )
    return scaled


_ENTRY_ROOM_PRIORITY = (
    "foyer",
    "verandah",
    "living",
    "drawing",
    "family_lounge",
    "dining",
)


def _entry_room(problem: CompiledConstraintProblem) -> Any | None:
    for room_type in _ENTRY_ROOM_PRIORITY:
        matches = tuple(
            room for room in problem.room_instances if room.room_type.value == room_type
        )
        if matches:
            return min(matches, key=lambda item: str(item.id))
    return None


def _apply_residential_boundary_constraints(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
    width_cells: int,
    depth_cells: int,
    notices: list[PlannerNotice],
) -> None:
    planning = config.residential_planning
    if not planning.enabled:
        return

    parking_rooms = tuple(
        room for room in problem.room_instances if room.room_type.value in {"parking", "garage"}
    )
    if planning.require_road_connected_parking and parking_rooms:
        if planning.road_boundary_side is None:
            raise SolverModelError(
                "Road-connected parking requires a deterministic local road boundary side."
            )
        for room in parking_rooms:
            room_var = room_vars[room.id]
            _pin_room_to_boundary(
                model,
                room_var,
                side=planning.road_boundary_side,
                width_cells=width_cells,
                depth_cells=depth_cells,
            )
            _apply_parking_clear_dimension_constraints(
                model,
                room_var,
                side=planning.road_boundary_side,
                planning=planning,
            )
        _append_notice(
            notices,
            code="ROAD_CONNECTED_PARKING_ENFORCED",
            message=(
                "Parking/garage room envelopes are pinned to the confirmed road-side "
                "boundary before architectural geometry is built."
            ),
        )

    if planning.require_entrance_boundary_access:
        if planning.entrance_boundary_side is None:
            raise SolverModelError(
                "Entrance-boundary access requires a deterministic local entrance side."
            )
        entry = _entry_room(problem)
        if entry is None:
            raise SolverModelError("Residential entrance anchoring requires an entry-capable room.")
        _pin_room_to_boundary(
            model,
            room_vars[entry.id],
            side=planning.entrance_boundary_side,
            width_cells=width_cells,
            depth_cells=depth_cells,
        )
        _append_notice(
            notices,
            code="ENTRANCE_BOUNDARY_ANCHOR_ENFORCED",
            message=(
                f"Entry room {entry.room_type.value} is pinned to the confirmed "
                "entrance-facing boundary."
            ),
            room_instance_id=entry.id,
        )


def _apply_vertical_core_reservation(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
    bounds: _RectangleBounds,
    notices: list[PlannerNotice],
) -> None:
    footprint = config.residential_planning.vertical_core_footprint
    if footprint is None:
        return

    staircase_rooms = tuple(
        room for room in problem.room_instances if room.room_type is RoomType.STAIRCASE
    )
    if len(staircase_rooms) != 1:
        raise SolverModelError(
            "A vertical-core reservation requires exactly one staircase room per floor."
        )

    xs = {point.x_mm for point in footprint.outer}
    ys = {point.y_mm for point in footprint.outer}
    if len(xs) != 2 or len(ys) != 2 or len(footprint.outer) != 4:
        raise SolverModelError("Vertical-core reservation must be a rectangular footprint.")

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    values_mm = (
        min_x - bounds.min_x_mm,
        min_y - bounds.min_y_mm,
        max_x - min_x,
        max_y - min_y,
    )
    step = config.solver_step_mm
    if any(value < 0 or value % step for value in values_mm):
        raise SolverModelError(
            "Vertical-core reservation must lie on the configured solver lattice."
        )

    x_cells, y_cells, width_cells, depth_cells = (
        value // step for value in values_mm
    )
    room = room_vars[staircase_rooms[0].id]
    model.add(room.x == x_cells)
    model.add(room.y == y_cells)
    model.add(room.width == width_cells)
    model.add(room.depth == depth_cells)
    _append_notice(
        notices,
        code="VERTICAL_CORE_RESERVED",
        message=(
            "The staircase room envelope was pinned to the building-level vertical-core "
            "reservation before room geometry was finalized."
        ),
        room_instance_id=staircase_rooms[0].id,
    )


def _append_wet_stack_objectives(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
    bounds: _RectangleBounds,
    width_cells: int,
    depth_cells: int,
    notices: list[PlannerNotice],
    penalty_terms: list[_PenaltyTerm],
) -> None:
    planning = config.residential_planning
    fallback_anchor = planning.wet_stack_anchor
    stack_targets = planning.wet_stack_targets
    if (
        fallback_anchor is None
        and not stack_targets
    ) or planning.wet_stack_weight == 0:
        return

    step = config.solver_step_mm
    max_distance2_cells = (width_cells + depth_cells) * 2
    added = 0
    used_cross_floor_targets = 0

    def target_center2(anchor: Any) -> tuple[int, int]:
        return (
            ((anchor.x_mm - bounds.min_x_mm) * 2) // step,
            ((anchor.y_mm - bounds.min_y_mm) * 2) // step,
        )

    def distance_to_anchor(
        *,
        room_id: Any,
        values: _RoomVars,
        anchor: Any,
        suffix: str,
    ) -> Any:
        target_x2, target_y2 = target_center2(anchor)
        dx = model.new_int_var(
            0,
            width_cells * 2,
            f"wet_stack_dx_{room_id.hex}_{suffix}",
        )
        dy = model.new_int_var(
            0,
            depth_cells * 2,
            f"wet_stack_dy_{room_id.hex}_{suffix}",
        )
        model.add_abs_equality(dx, values.x * 2 + values.width - target_x2)
        model.add_abs_equality(dy, values.y * 2 + values.depth - target_y2)
        distance2 = model.new_int_var(
            0,
            max_distance2_cells,
            f"wet_stack_distance2_{room_id.hex}_{suffix}",
        )
        model.add(distance2 == dx + dy)
        return distance2

    for room in sorted(problem.room_instances, key=lambda item: str(item.id)):
        if room.room_type not in _WET_ROOM_TYPES:
            continue

        values = room_vars[room.id]
        compatible_targets = tuple(
            anchor
            for target_room_type, anchor in stack_targets
            if _wet_stack_group(target_room_type) == _wet_stack_group(room.room_type)
        )

        if compatible_targets:
            candidate_distances = tuple(
                distance_to_anchor(
                    room_id=room.id,
                    values=values,
                    anchor=anchor,
                    suffix=f"lower_{index}",
                )
                for index, anchor in enumerate(compatible_targets)
            )
            if len(candidate_distances) == 1:
                minimum_distance2 = candidate_distances[0]
            else:
                minimum_distance2 = model.new_int_var(
                    0,
                    max_distance2_cells,
                    f"wet_stack_min_distance2_{room.id.hex}",
                )
                model.add_min_equality(minimum_distance2, candidate_distances)

            physical_distance2_mm = model.new_int_var(
                0,
                max_distance2_cells * step,
                f"wet_stack_distance2_mm_{room.id.hex}",
            )
            model.add(physical_distance2_mm == minimum_distance2 * step)
            penalty = physical_distance2_mm
            used_cross_floor_targets += 1
        elif fallback_anchor is not None:
            penalty = distance_to_anchor(
                room_id=room.id,
                values=values,
                anchor=fallback_anchor,
                suffix="core",
            )
        else:
            continue

        penalty_terms.append(
            _PenaltyTerm(
                _system_objective_id(problem, f"wet-stack:{room.id}"),
                "WET_STACK_PROXIMITY",
                planning.wet_stack_weight,
                penalty,
            )
        )
        added += 1

    if added:
        detail = (
            f"{used_cross_floor_targets} room(s) used nearest compatible "
            "lower-floor canonical wet/service geometry; remaining rooms used "
            "the building-core plumbing-zone fallback."
            if used_cross_floor_targets
            else "The building-core plumbing-zone fallback was used."
        )
        _append_notice(
            notices,
            code="WET_STACK_PROXIMITY_ACTIVE",
            message=(
                f"{added} wet/service room(s) received a soft plumbing-zone "
                f"proximity objective. {detail} Exact cross-floor replication "
                "was not required."
            ),
        )


def _relationship_already_declared(
    problem: CompiledConstraintProblem,
    *,
    source_room_id: Any,
    target_room_type: RoomType,
) -> bool:
    for item in (*problem.hard_constraints, *problem.soft_constraints):
        if getattr(item, "room_instance_id", None) != source_room_id:
            continue
        if getattr(item, "target_room_type", None) is target_room_type:
            return True
    return False


def _topology_target(
    room_type: RoomType,
    present: set[RoomType],
) -> tuple[RoomType, int, int] | None:
    private_types = {
        RoomType.BEDROOM,
        RoomType.MASTER_BEDROOM,
        RoomType.PARENTS_BEDROOM,
        RoomType.GUEST_BEDROOM,
        RoomType.CHILDREN_BEDROOM,
        RoomType.COMMON_TOILET,
        RoomType.BATH,
        RoomType.POWDER_ROOM,
    }
    if room_type in private_types:
        if RoomType.LOBBY in present:
            return (RoomType.LOBBY, 100, 1_100)
        if RoomType.LIVING in present:
            return (RoomType.LIVING, 90, 1_100)

    if room_type is RoomType.LOBBY:
        if RoomType.FOYER in present:
            return (RoomType.FOYER, 100, 1_100)
        if RoomType.LIVING in present:
            return (RoomType.LIVING, 100, 1_100)
        if RoomType.DRAWING in present:
            return (RoomType.DRAWING, 100, 1_100)

    if room_type is RoomType.STAIRCASE:
        if RoomType.LOBBY in present:
            return (RoomType.LOBBY, 100, 1_100)
        if RoomType.CORRIDOR in present:
            return (RoomType.CORRIDOR, 100, 1_100)
        if RoomType.FOYER in present:
            return (RoomType.FOYER, 100, 1_100)

    if room_type is RoomType.KITCHEN:
        if RoomType.DINING in present:
            return (RoomType.DINING, 95, 1_100)
        if RoomType.LIVING in present:
            return (RoomType.LIVING, 85, 1_100)

    if room_type is RoomType.PUJA:
        if RoomType.DINING in present:
            return (RoomType.DINING, 75, 900)
        if RoomType.LIVING in present:
            return (RoomType.LIVING, 75, 900)

    if room_type in {RoomType.PARKING, RoomType.GARAGE}:
        if RoomType.FOYER in present:
            return (RoomType.FOYER, 80, 1_100)
        if RoomType.LIVING in present:
            return (RoomType.LIVING, 80, 1_100)

    if (
        room_type
        in {
            RoomType.UTILITY,
            RoomType.PANTRY,
            RoomType.STORE,
            RoomType.LAUNDRY,
        }
        and RoomType.KITCHEN in present
    ):
        return (RoomType.KITCHEN, 85, 1_000)

    if room_type is RoomType.SERVANT_TOILET and RoomType.SERVANT_ROOM in present:
        return (RoomType.SERVANT_ROOM, 95, 900)

    return None


def _append_residential_topology_objectives(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
    width_cells: int,
    depth_cells: int,
    notices: list[PlannerNotice],
    penalty_terms: list[_PenaltyTerm],
) -> None:
    if not config.residential_planning.enabled:
        return

    present = {room.room_type for room in problem.room_instances}
    added = 0
    for room in sorted(problem.room_instances, key=lambda item: str(item.id)):
        if room.room_type in {RoomType.PARKING, RoomType.GARAGE}:
            continue
        target = _topology_target(room.room_type, present)
        if target is None:
            continue
        target_room_type, weight, shared_length_mm = target
        if target_room_type is room.room_type:
            continue
        if _relationship_already_declared(
            problem,
            source_room_id=room.id,
            target_room_type=target_room_type,
        ):
            continue

        targets = tuple(
            target_room
            for target_room in problem.room_instances
            if target_room.room_type is target_room_type and target_room.id != room.id
        )
        if not targets:
            continue

        spec = _AdjacencyTargetSpec(
            max_gap_mm=0,
            min_shared_length_mm=shared_length_mm,
        )
        pair_penalties = [
            _adjacency_pair_penalty(
                model,
                room_vars[room.id],
                room_vars[target_room.id],
                config=config,
                buildable_width_cells=width_cells,
                buildable_depth_cells=depth_cells,
                objective=spec,
                name=(f"res_topology_{room.id.hex}_{target_room.id.hex}"),
            )
            for target_room in targets
        ]
        if len(pair_penalties) == 1:
            best = pair_penalties[0]
        else:
            upper = (width_cells + depth_cells) * config.solver_step_mm + shared_length_mm
            best = model.new_int_var(
                0,
                upper,
                f"res_topology_best_{room.id.hex}",
            )
            model.add_min_equality(best, pair_penalties)

        penalty_terms.append(
            _PenaltyTerm(
                _system_objective_id(
                    problem,
                    f"topology:{room.id}:{target_room_type.value}",
                ),
                "RESIDENTIAL_TOPOLOGY_ADJACENCY",
                weight,
                best,
            )
        )
        added += 1

    if added:
        _append_notice(
            notices,
            code="RESIDENTIAL_TOPOLOGY_ACTIVE",
            message=(
                f"{added} deterministic residential topology objective(s) were "
                "added where no explicit relationship already governed the pair."
            ),
        )


def _append_hard_residential_circulation(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
    width_cells: int,
    depth_cells: int,
    notices: list[PlannerNotice],
) -> None:
    if not config.residential_planning.require_horizontal_circulation:
        return

    present = {room.room_type for room in problem.room_instances}
    added = 0
    for room in sorted(problem.room_instances, key=lambda item: str(item.id)):
        if room.room_type in {RoomType.PARKING, RoomType.GARAGE}:
            continue
        target = _topology_target(room.room_type, present)
        if target is None:
            continue
        target_room_type, _weight, shared_length_mm = target
        targets = tuple(
            item
            for item in problem.room_instances
            if item.room_type is target_room_type and item.id != room.id
        )
        if not targets:
            continue
        penalties = [
            _adjacency_pair_penalty(
                model,
                room_vars[room.id],
                room_vars[item.id],
                config=config,
                buildable_width_cells=width_cells,
                buildable_depth_cells=depth_cells,
                objective=_AdjacencyTargetSpec(
                    max_gap_mm=0,
                    min_shared_length_mm=shared_length_mm,
                ),
                name=f"hard_circulation_{room.id.hex}_{item.id.hex}",
            )
            for item in targets
        ]
        if len(penalties) == 1:
            best = penalties[0]
        else:
            upper = (width_cells + depth_cells) * config.solver_step_mm + shared_length_mm
            best = model.new_int_var(0, upper, f"hard_circulation_best_{room.id.hex}")
            model.add_min_equality(best, penalties)
        model.add(best == 0)
        added += 1

    if added:
        _append_notice(
            notices,
            code="RESIDENTIAL_CIRCULATION_HARD",
            message=(
                f"{added} hard per-room circulation relation(s) were enforced before "
                "canonical geometry and opening synthesis."
            ),
        )


def _append_circulation_repair_constraints(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
    width_cells: int,
    depth_cells: int,
    notices: list[PlannerNotice],
) -> None:
    pairs = config.residential_planning.circulation_repair_pairs
    if not pairs:
        return

    room_ids = {room.id for room in problem.room_instances}
    added = 0
    for pair in sorted(
        pairs,
        key=lambda item: (str(item.first_room_id), str(item.second_room_id)),
    ):
        if pair.first_room_id not in room_ids or pair.second_room_id not in room_ids:
            raise SolverModelError(
                "Circulation repair references a room outside the compiled problem."
            )

        penalty = _adjacency_pair_penalty(
            model,
            room_vars[pair.first_room_id],
            room_vars[pair.second_room_id],
            config=config,
            buildable_width_cells=width_cells,
            buildable_depth_cells=depth_cells,
            objective=_AdjacencyTargetSpec(
                max_gap_mm=0,
                min_shared_length_mm=pair.min_shared_length_mm,
            ),
            name=(
                "circulation_repair_"
                f"{pair.first_room_id.hex}_{pair.second_room_id.hex}"
            ),
        )
        model.add(penalty == 0)
        added += 1

    _append_notice(
        notices,
        code="CIRCULATION_REPAIR_ENFORCED",
        message=(
            f"{added} system-derived circulation repair adjacency constraint(s) "
            "were enforced after a prior solved layout proved disconnected."
        ),
    )


def _append_residential_quality_objectives(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    minimum_envelope_area_mm2: dict[Any, int],
    *,
    config: PlannerConfig,
    bounds: _RectangleBounds,
    width_cells: int,
    depth_cells: int,
    notices: list[PlannerNotice],
    penalty_terms: list[_PenaltyTerm],
) -> None:
    planning = config.residential_planning
    if not planning.enabled:
        return

    step2 = config.solver_step_mm * config.solver_step_mm
    buildable_area_mm2 = bounds.width_mm * bounds.depth_mm
    desired_area_mm2 = buildable_area_mm2 * planning.target_occupied_area_basis_points // 10_000
    bases = tuple(
        RoomAreaBasis(
            room_instance_id=room.id,
            room_type=room.room_type,
            minimum_envelope_area_mm2=minimum_envelope_area_mm2[room.id],
        )
        for room in problem.room_instances
    )
    targets = allocate_room_area_targets(
        bases,
        desired_total_area_mm2=desired_area_mm2,
    )
    effective_target_mm2 = sum(item.target_area_mm2 for item in targets)

    total_area_cells2 = model.new_int_var(
        0,
        width_cells * depth_cells,
        "residential_total_area_cells2",
    )
    model.add(
        total_area_cells2 == sum(room_vars[room.id].area_cells2 for room in problem.room_instances)
    )
    total_area_mm2 = model.new_int_var(
        0,
        buildable_area_mm2,
        "residential_total_area_mm2",
    )
    model.add(total_area_mm2 == total_area_cells2 * step2)

    if planning.occupied_area_weight > 0:
        deviation = model.new_int_var(
            0,
            buildable_area_mm2,
            "residential_total_area_deviation_mm2",
        )
        model.add_abs_equality(deviation, total_area_mm2 - effective_target_mm2)
        scaled = _scaled_area_penalty(
            model,
            raw_penalty_mm2=deviation,
            upper_mm2=buildable_area_mm2,
            name="residential_total_area_penalty",
        )
        penalty_terms.append(
            _PenaltyTerm(
                _system_objective_id(problem, "occupied-area-target"),
                "RESIDENTIAL_OCCUPIED_AREA_TARGET",
                planning.occupied_area_weight,
                scaled,
            )
        )

    target_by_room = {item.room_instance_id: item for item in targets}
    if planning.room_area_balance_weight > 0:
        for room in problem.room_instances:
            target = target_by_room[room.id]
            deviation = model.new_int_var(
                0,
                buildable_area_mm2,
                f"residential_room_area_deviation_{room.id.hex}",
            )
            model.add_abs_equality(
                deviation,
                room_vars[room.id].area_cells2 * step2 - target.target_area_mm2,
            )
            scaled = _scaled_area_penalty(
                model,
                raw_penalty_mm2=deviation,
                upper_mm2=buildable_area_mm2,
                name=f"residential_room_area_penalty_{room.id.hex}",
            )
            penalty_terms.append(
                _PenaltyTerm(
                    _system_objective_id(problem, f"room-area:{room.id}"),
                    "RESIDENTIAL_ROOM_AREA_BALANCE",
                    planning.room_area_balance_weight,
                    scaled,
                )
            )

    if planning.compactness_weight > 0:
        min_x = model.new_int_var(0, width_cells, "residential_bbox_min_x")
        min_y = model.new_int_var(0, depth_cells, "residential_bbox_min_y")
        max_x = model.new_int_var(0, width_cells, "residential_bbox_max_x")
        max_y = model.new_int_var(0, depth_cells, "residential_bbox_max_y")
        model.add_min_equality(
            min_x,
            [room_vars[room.id].x for room in problem.room_instances],
        )
        model.add_min_equality(
            min_y,
            [room_vars[room.id].y for room in problem.room_instances],
        )
        model.add_max_equality(
            max_x,
            [room_vars[room.id].x_end for room in problem.room_instances],
        )
        model.add_max_equality(
            max_y,
            [room_vars[room.id].y_end for room in problem.room_instances],
        )
        span_x = model.new_int_var(1, width_cells, "residential_bbox_span_x")
        span_y = model.new_int_var(1, depth_cells, "residential_bbox_span_y")
        model.add(span_x == max_x - min_x)
        model.add(span_y == max_y - min_y)
        bbox_cells2 = model.new_int_var(
            1,
            width_cells * depth_cells,
            "residential_bbox_area_cells2",
        )
        model.add_multiplication_equality(bbox_cells2, [span_x, span_y])
        void_cells2 = model.new_int_var(
            0,
            width_cells * depth_cells,
            "residential_bbox_void_cells2",
        )
        model.add(void_cells2 == bbox_cells2 - total_area_cells2)
        void_mm2 = model.new_int_var(
            0,
            buildable_area_mm2,
            "residential_bbox_void_mm2",
        )
        model.add(void_mm2 == void_cells2 * step2)
        scaled_void = _scaled_area_penalty(
            model,
            raw_penalty_mm2=void_mm2,
            upper_mm2=buildable_area_mm2,
            name="residential_compactness_penalty",
        )
        penalty_terms.append(
            _PenaltyTerm(
                _system_objective_id(problem, "compactness-void"),
                "RESIDENTIAL_COMPACTNESS_VOID",
                planning.compactness_weight,
                scaled_void,
            )
        )

    actual_target_bp = (
        effective_target_mm2 * 10_000 + buildable_area_mm2 // 2
    ) // buildable_area_mm2
    _append_notice(
        notices,
        code="RESIDENTIAL_PLANNING_TARGET_ACTIVE",
        message=(
            "Automatic occupied-room planning target is "
            f"{actual_target_bp / 100:.1f}% of the buildable rectangle after "
            "room-role expansion caps. This is a planning heuristic, not a "
            "regulatory/FAR/FSI entitlement."
        ),
    )
    _append_notice(
        notices,
        code="RESIDENTIAL_COMPACTNESS_ACTIVE",
        message=(
            "The solver penalizes empty area inside the occupied-room bounding box "
            "to reduce scattered islands and unexplained internal voids."
        ),
    )


def _rectangle_bounds(polygon: IntPolygon) -> _RectangleBounds:
    if polygon.holes:
        raise UnsupportedSolverProblemError(
            "Phase 7 CP-SAT planner supports rectangular buildable areas without holes only."
        )
    if len(polygon.outer) != 4:
        raise UnsupportedSolverProblemError(
            "Phase 7 CP-SAT planner supports four-corner rectangular buildable areas only."
        )

    xs = [point.x_mm for point in polygon.outer]
    ys = [point.y_mm for point in polygon.outer]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    if min_x == max_x or min_y == max_y:
        raise SolverModelError("Buildable rectangle must have positive width and depth.")
    expected = {
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    }
    actual = {(point.x_mm, point.y_mm) for point in polygon.outer}
    if actual != expected:
        raise UnsupportedSolverProblemError(
            "Phase 7 CP-SAT planner requires an axis-aligned rectangular buildable area."
        )
    return _RectangleBounds(min_x, min_y, max_x - min_x, max_y - min_y)


def _status(value: Any) -> PlannerStatus:
    if value == cp_model.OPTIMAL:
        return PlannerStatus.OPTIMAL
    if value == cp_model.FEASIBLE:
        return PlannerStatus.FEASIBLE
    if value == cp_model.INFEASIBLE:
        return PlannerStatus.INFEASIBLE
    return PlannerStatus.UNKNOWN


def _append_notice(
    notices: list[PlannerNotice],
    *,
    code: str,
    message: str,
    constraint_id: Any | None = None,
    room_instance_id: Any | None = None,
) -> None:
    notices.append(
        PlannerNotice(
            code=code,
            severity=PlannerNoticeSeverity.INFO,
            message=message,
            constraint_id=constraint_id,
            room_instance_id=room_instance_id,
        )
    )


def _room_constraint_index(problem: CompiledConstraintProblem) -> dict[Any, list[Any]]:
    result: dict[Any, list[Any]] = {room.id: [] for room in problem.room_instances}
    for constraint in problem.hard_constraints:
        room_id = constraint.room_instance_id
        result.setdefault(room_id, []).append(constraint)
    return result


def _target_rooms(problem: CompiledConstraintProblem, room_type: Any) -> tuple[Any, ...]:
    return tuple(room for room in problem.room_instances if room.room_type == room_type)


def _new_nonnegative_max(
    model: Any,
    expressions: list[Any],
    upper: int,
    name: str,
) -> Any:
    var = model.new_int_var(0, upper, name)
    model.add_max_equality(var, [0, *expressions])
    return var


def _append_hard_adjacency_prohibitions(
    model: Any,
    problem: CompiledConstraintProblem,
    room_vars: dict[Any, _RoomVars],
    *,
    config: PlannerConfig,
) -> None:
    """Enforce physical separation for every hard adjacency prohibition.

    For ordinary user-authored prohibitions, at least one solver lattice step
    separates the room envelopes.

    Architectural invariants use the configured clearance reserve so the
    prohibited spaces cannot merely touch at a wall.
    """

    pair_gap_cells: dict[
        tuple[Any, Any],
        int,
    ] = {}

    for constraint in sorted(
        (
            item
            for item in problem.hard_constraints
            if isinstance(
                item,
                AdjacencyProhibitionConstraint,
            )
        ),
        key=lambda item: str(item.id),
    ):
        source_room = next(
            (room for room in problem.room_instances if room.id == constraint.room_instance_id),
            None,
        )

        if source_room is None:
            raise SolverModelError("Adjacency prohibition references an unknown source room.")

        targets = _target_rooms(
            problem,
            constraint.target_room_type,
        )

        for target_room in targets:
            if target_room.id == source_room.id:
                continue

            if constraint.origin is ConstraintOrigin.ARCHITECTURAL_INVARIANT:
                required_gap_mm = max(
                    config.solver_step_mm,
                    config.clearance_reserve_mm,
                )
            else:
                required_gap_mm = config.solver_step_mm

            gap_cells = max(
                1,
                (required_gap_mm + config.solver_step_mm - 1) // config.solver_step_mm,
            )

            first_id, second_id = sorted(
                (
                    source_room.id,
                    target_room.id,
                ),
                key=str,
            )

            key = (
                first_id,
                second_id,
            )

            pair_gap_cells[key] = max(
                pair_gap_cells.get(key, 0),
                gap_cells,
            )

    for (
        first_id,
        second_id,
    ), gap_cells in sorted(
        pair_gap_cells.items(),
        key=lambda item: (
            str(item[0][0]),
            str(item[0][1]),
        ),
    ):
        first = room_vars[first_id]
        second = room_vars[second_id]

        prefix = f"hard_adj_{str(first_id).replace('-', '')}_{str(second_id).replace('-', '')}"

        first_left = model.new_bool_var(f"{prefix}_first_left")
        second_left = model.new_bool_var(f"{prefix}_second_left")
        first_below = model.new_bool_var(f"{prefix}_first_below")
        second_below = model.new_bool_var(f"{prefix}_second_below")

        model.add(first.x_end + gap_cells <= second.x).only_enforce_if(first_left)

        model.add(second.x_end + gap_cells <= first.x).only_enforce_if(second_left)

        model.add(first.y_end + gap_cells <= second.y).only_enforce_if(first_below)

        model.add(second.y_end + gap_cells <= first.y).only_enforce_if(second_below)

        model.add_bool_or(
            [
                first_left,
                second_left,
                first_below,
                second_below,
            ]
        )


def _adjacency_pair_penalty(
    model: Any,
    source: _RoomVars,
    target: _RoomVars,
    *,
    config: PlannerConfig,
    buildable_width_cells: int,
    buildable_depth_cells: int,
    objective: AdjacencyPreferenceObjective | _AdjacencyTargetSpec,
    name: str,
) -> Any:
    gap_x = _new_nonnegative_max(
        model,
        [source.x - target.x_end, target.x - source.x_end],
        buildable_width_cells,
        f"{name}_gap_x",
    )
    gap_y = _new_nonnegative_max(
        model,
        [source.y - target.y_end, target.y - source.y_end],
        buildable_depth_cells,
        f"{name}_gap_y",
    )
    gap = model.new_int_var(
        0,
        buildable_width_cells + buildable_depth_cells,
        f"{name}_gap",
    )
    model.add(gap == gap_x + gap_y)

    gap_mm = model.new_int_var(
        0,
        (buildable_width_cells + buildable_depth_cells) * config.solver_step_mm,
        f"{name}_gap_mm",
    )
    model.add(gap_mm == gap * config.solver_step_mm)

    penalties: list[Any] = []
    if objective.max_gap_mm is None:
        penalties.append(gap_mm)
    else:
        excess_mm = _new_nonnegative_max(
            model,
            [gap * config.solver_step_mm - objective.max_gap_mm],
            (buildable_width_cells + buildable_depth_cells) * config.solver_step_mm,
            f"{name}_gap_excess_mm",
        )
        penalties.append(excess_mm)

    if objective.min_shared_length_mm is not None:
        min_x_end = model.new_int_var(0, buildable_width_cells, f"{name}_min_x_end")
        max_x_start = model.new_int_var(0, buildable_width_cells, f"{name}_max_x_start")
        model.add_min_equality(min_x_end, [source.x_end, target.x_end])
        model.add_max_equality(max_x_start, [source.x, target.x])
        overlap_x = _new_nonnegative_max(
            model,
            [min_x_end - max_x_start],
            buildable_width_cells,
            f"{name}_overlap_x",
        )

        min_y_end = model.new_int_var(0, buildable_depth_cells, f"{name}_min_y_end")
        max_y_start = model.new_int_var(0, buildable_depth_cells, f"{name}_max_y_start")
        model.add_min_equality(min_y_end, [source.y_end, target.y_end])
        model.add_max_equality(max_y_start, [source.y, target.y])
        overlap_y = _new_nonnegative_max(
            model,
            [min_y_end - max_y_start],
            buildable_depth_cells,
            f"{name}_overlap_y",
        )
        shared = model.new_int_var(
            0,
            max(buildable_width_cells, buildable_depth_cells),
            f"{name}_shared",
        )
        model.add_max_equality(shared, [overlap_x, overlap_y])
        shortfall_mm = _new_nonnegative_max(
            model,
            [objective.min_shared_length_mm - shared * config.solver_step_mm],
            objective.min_shared_length_mm,
            f"{name}_shared_shortfall_mm",
        )
        penalties.append(shortfall_mm)

    if len(penalties) == 1:
        return penalties[0]
    total_upper = (buildable_width_cells + buildable_depth_cells) * config.solver_step_mm + (
        objective.min_shared_length_mm or 0
    )
    total = model.new_int_var(0, total_upper, f"{name}_pair_penalty")
    model.add(total == sum(penalties))
    return total


def solve_rectangular_problem(
    problem: CompiledConstraintProblem,
    *,
    config: PlannerConfig,
) -> PlannerResult:
    """Solve a Phase 7 single-floor rectangular-room problem with OR-Tools CP-SAT.

    The canonical output remains integer millimetres. ``solver_step_mm`` controls the search
    lattice only; every emitted coordinate and dimension is converted back to exact integer mm.
    Unsupported hard semantics fail closed instead of being silently ignored.
    """

    if len(problem.available_floor_indices) != 1:
        raise UnsupportedSolverProblemError("Phase 7 planner supports exactly one available floor.")
    if any(room.locked for room in problem.room_instances):
        raise UnsupportedSolverProblemError(
            "Locked rooms require existing authoritative geometry and are not supported in Phase 7."
        )

    bounds = _rectangle_bounds(problem.buildable_area.polygon)
    step = config.solver_step_mm
    width_cells = bounds.width_mm // step
    depth_cells = bounds.depth_mm // step
    if width_cells <= 0 or depth_cells <= 0:
        raise SolverModelError("solver_step_mm is larger than the buildable rectangle.")

    model = cp_model.CpModel()
    room_vars: dict[Any, _RoomVars] = {}
    minimum_envelope_area_mm2: dict[Any, int] = {}
    hard_by_room = _room_constraint_index(problem)
    ordered_rooms = tuple(sorted(problem.room_instances, key=lambda item: str(item.id)))
    if config.search_variant in {
        PlannerSearchVariant.REVERSE_LOWER_LEFT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    }:
        ordered_rooms = tuple(reversed(ordered_rooms))

    for room in ordered_rooms:
        constraints = hard_by_room.get(room.id, [])
        min_width_mm = 1
        min_depth_mm = 1
        max_width_mm = bounds.width_mm
        max_depth_mm = bounds.depth_mm
        min_area_mm2 = 1
        max_area_mm2 = bounds.width_mm * bounds.depth_mm
        aspect: AspectRatioConstraint | None = None

        for constraint in constraints:
            if isinstance(constraint, MinimumDimensionConstraint):
                if constraint.axis is DimensionAxis.WIDTH:
                    min_width_mm = max(min_width_mm, constraint.minimum_mm)
                else:
                    min_depth_mm = max(min_depth_mm, constraint.minimum_mm)
            elif isinstance(constraint, MaximumDimensionConstraint):
                if constraint.axis is DimensionAxis.WIDTH:
                    max_width_mm = min(max_width_mm, constraint.maximum_mm)
                else:
                    max_depth_mm = min(max_depth_mm, constraint.maximum_mm)
            elif isinstance(constraint, MinimumAreaConstraint):
                min_area_mm2 = max(min_area_mm2, constraint.minimum_area_mm2)
            elif isinstance(constraint, MaximumAreaConstraint):
                max_area_mm2 = min(max_area_mm2, constraint.maximum_area_mm2)
            elif isinstance(constraint, AspectRatioConstraint):
                aspect = constraint
            elif isinstance(constraint, ContainmentConstraint):
                pass
            elif isinstance(constraint, AvailableFloorsConstraint):
                floor_index = problem.available_floor_indices[0]
                if floor_index not in constraint.allowed_floor_indices:
                    raise SolverModelError(
                        f"Room {room.id} cannot be placed on the only available floor."
                    )
            elif isinstance(constraint, AdjacencyProhibitionConstraint):
                # Applied after every room variable exists.
                pass
            else:
                raise UnsupportedSolverProblemError(
                    f"Unsupported hard constraint in Phase 7: {constraint.kind}."
                )

        reserve_mm = config.clearance_reserve_mm
        min_w_cells = (min_width_mm + reserve_mm + step - 1) // step
        min_d_cells = (min_depth_mm + reserve_mm + step - 1) // step
        max_w_cells = min(width_cells, max_width_mm // step)
        max_d_cells = min(depth_cells, max_depth_mm // step)
        if min_w_cells > max_w_cells or min_d_cells > max_d_cells:
            return _empty_result(
                problem,
                config,
                PlannerStatus.INFEASIBLE,
                notice=(
                    "Room dimension bounds contain no value on the configured solver "
                    "lattice after applying the explicit clearance reserve."
                ),
            )

        prefix = f"room_{room.id.hex}"
        width = model.new_int_var(min_w_cells, max_w_cells, f"{prefix}_w")
        depth = model.new_int_var(min_d_cells, max_d_cells, f"{prefix}_d")
        x = model.new_int_var(0, width_cells - min_w_cells, f"{prefix}_x")
        y = model.new_int_var(0, depth_cells - min_d_cells, f"{prefix}_y")
        x_end = model.new_int_var(min_w_cells, width_cells, f"{prefix}_x2")
        y_end = model.new_int_var(min_d_cells, depth_cells, f"{prefix}_y2")
        model.add(x_end == x + width)
        model.add(y_end == y + depth)
        model.add(x_end <= width_cells)
        model.add(y_end <= depth_cells)

        area_cells2 = model.new_int_var(
            min_w_cells * min_d_cells,
            max_w_cells * max_d_cells,
            f"{prefix}_area",
        )
        model.add_multiplication_equality(area_cells2, [width, depth])

        # Phase 9 validates room minima on clear dimensions after wall
        # thickness is deducted from the wall-centreline envelope. The
        # explicit reserve is therefore subtracted before enforcing minimum
        # dimensions/area. Using the maximum wall thickness is conservative:
        # actual clear geometry can only be equal or larger.
        clear_width_mm = model.new_int_var(
            1,
            bounds.width_mm,
            f"{prefix}_clear_w_mm",
        )
        clear_depth_mm = model.new_int_var(
            1,
            bounds.depth_mm,
            f"{prefix}_clear_d_mm",
        )
        model.add(clear_width_mm == width * step - reserve_mm)
        model.add(clear_depth_mm == depth * step - reserve_mm)

        clear_area_mm2 = model.new_int_var(
            1,
            bounds.width_mm * bounds.depth_mm,
            f"{prefix}_clear_area_mm2",
        )
        model.add_multiplication_equality(
            clear_area_mm2,
            [clear_width_mm, clear_depth_mm],
        )
        model.add(clear_area_mm2 >= min_area_mm2)

        # Preserve the existing maximum-area contract on the solver envelope.
        # The commercial generation profile does not currently set maxima.
        step2 = step * step
        model.add(area_cells2 * step2 <= max_area_mm2)

        if aspect is not None:
            model.add(width * 1000 >= depth * aspect.min_ratio_milli)
            model.add(width * 1000 <= depth * aspect.max_ratio_milli)

        x_interval = model.new_interval_var(x, width, x_end, f"{prefix}_xi")
        y_interval = model.new_interval_var(y, depth, y_end, f"{prefix}_yi")
        room_vars[room.id] = _RoomVars(
            x=x,
            y=y,
            width=width,
            depth=depth,
            x_end=x_end,
            y_end=y_end,
            area_cells2=area_cells2,
            clear_width_mm=clear_width_mm,
            clear_depth_mm=clear_depth_mm,
            clear_area_mm2=clear_area_mm2,
            x_interval=x_interval,
            y_interval=y_interval,
        )
        minimum_envelope_area_mm2[room.id] = min_w_cells * min_d_cells * step2

    model.add_no_overlap_2d(
        [room_vars[room.id].x_interval for room in ordered_rooms],
        [room_vars[room.id].y_interval for room in ordered_rooms],
    )

    _append_hard_adjacency_prohibitions(
        model,
        problem,
        room_vars,
        config=config,
    )

    notices: list[PlannerNotice] = []
    _apply_residential_boundary_constraints(
        model,
        problem,
        room_vars,
        config=config,
        width_cells=width_cells,
        depth_cells=depth_cells,
        notices=notices,
    )
    _apply_vertical_core_reservation(
        model,
        problem,
        room_vars,
        config=config,
        bounds=bounds,
        notices=notices,
    )

    penalty_terms: list[_PenaltyTerm] = []
    for objective in sorted(problem.soft_constraints, key=lambda item: str(item.id)):
        vars_for_room = room_vars[objective.room_instance_id]
        if isinstance(objective, PreferredDimensionObjective):
            variable = (
                vars_for_room.width
                if objective.axis is DimensionAxis.WIDTH
                else vars_for_room.depth
            )
            max_dimension_mm = (
                bounds.width_mm if objective.axis is DimensionAxis.WIDTH else bounds.depth_mm
            )
            deviation = model.new_int_var(0, max_dimension_mm, f"pref_dim_{objective.id.hex}")
            model.add_abs_equality(
                deviation,
                variable * step - objective.preferred_mm,
            )
            penalty_terms.append(
                _PenaltyTerm(objective.id, objective.kind.value, objective.weight, deviation)
            )
        elif isinstance(objective, AdjacencyPreferenceObjective):
            targets = tuple(
                room
                for room in _target_rooms(problem, objective.target_room_type)
                if room.id != objective.room_instance_id
            )
            if not targets:
                raise SolverModelError(
                    f"Adjacency objective {objective.id} has no target room instance."
                )
            pair_penalties = [
                _adjacency_pair_penalty(
                    model,
                    vars_for_room,
                    room_vars[target.id],
                    config=config,
                    buildable_width_cells=width_cells,
                    buildable_depth_cells=depth_cells,
                    objective=objective,
                    name=f"adj_{objective.id.hex}_{target.id.hex}",
                )
                for target in targets
            ]
            if len(pair_penalties) == 1:
                best = pair_penalties[0]
            else:
                upper = (bounds.width_mm + bounds.depth_mm) + (objective.min_shared_length_mm or 0)
                best = model.new_int_var(0, upper, f"adj_best_{objective.id.hex}")
                model.add_min_equality(best, pair_penalties)
            penalty_terms.append(
                _PenaltyTerm(objective.id, objective.kind.value, objective.weight, best)
            )
        elif isinstance(objective, FloorPreferenceObjective):
            _append_notice(
                notices,
                code="SINGLE_FLOOR_PREFERENCE_TRIVIALLY_SATISFIED",
                message=(
                    "Floor preference is trivially satisfied by the Phase 7 single-floor domain."
                ),
                constraint_id=objective.id,
                room_instance_id=objective.room_instance_id,
            )
        elif isinstance(objective, PreferredAreaObjective):
            deviation_mm2 = model.new_int_var(
                0,
                bounds.width_mm * bounds.depth_mm,
                f"pref_area_deviation_{objective.id.hex}",
            )
            model.add_abs_equality(
                deviation_mm2,
                vars_for_room.clear_area_mm2 - objective.preferred_area_mm2,
            )
            scaled = _scaled_area_penalty(
                model,
                raw_penalty_mm2=deviation_mm2,
                upper_mm2=bounds.width_mm * bounds.depth_mm,
                name=f"pref_area_penalty_{objective.id.hex}",
            )
            penalty_terms.append(
                _PenaltyTerm(
                    objective.id,
                    objective.kind.value,
                    objective.weight,
                    scaled,
                )
            )
        elif isinstance(objective, RoomPrioritiesObjective):
            _append_notice(
                notices,
                code="SOFT_OBJECTIVE_NOT_YET_OPTIMIZED",
                message=(
                    "Privacy/daylight/ventilation priorities require later architectural evidence "
                    "models and are not optimized in Phase 7."
                ),
                constraint_id=objective.id,
                room_instance_id=objective.room_instance_id,
            )
        elif isinstance(objective, AdjacencyAvoidanceObjective):
            _append_notice(
                notices,
                code="SOFT_OBJECTIVE_NOT_YET_OPTIMIZED",
                message="Soft adjacency avoidance is not optimized in Phase 7.",
                constraint_id=objective.id,
                room_instance_id=objective.room_instance_id,
            )

    _append_residential_topology_objectives(
        model,
        problem,
        room_vars,
        config=config,
        width_cells=width_cells,
        depth_cells=depth_cells,
        notices=notices,
        penalty_terms=penalty_terms,
    )

    _append_hard_residential_circulation(
        model,
        problem,
        room_vars,
        config=config,
        width_cells=width_cells,
        depth_cells=depth_cells,
        notices=notices,
    )

    _append_circulation_repair_constraints(
        model,
        problem,
        room_vars,
        config=config,
        width_cells=width_cells,
        depth_cells=depth_cells,
        notices=notices,
    )

    _append_wet_stack_objectives(
        model,
        problem,
        room_vars,
        config=config,
        bounds=bounds,
        width_cells=width_cells,
        depth_cells=depth_cells,
        notices=notices,
        penalty_terms=penalty_terms,
    )

    _append_residential_quality_objectives(
        model,
        problem,
        room_vars,
        minimum_envelope_area_mm2,
        config=config,
        bounds=bounds,
        width_cells=width_cells,
        depth_cells=depth_cells,
        notices=notices,
        penalty_terms=penalty_terms,
    )

    if penalty_terms:
        model.minimize(sum(term.expression * term.weight for term in penalty_terms))

    x_vars = [room_vars[room.id].x for room in ordered_rooms]
    y_vars = [room_vars[room.id].y for room in ordered_rooms]
    size_vars = [
        value
        for room in ordered_rooms
        for value in (room_vars[room.id].width, room_vars[room.id].depth)
    ]

    right_bias = config.search_variant in {
        PlannerSearchVariant.LOWER_RIGHT,
        PlannerSearchVariant.UPPER_RIGHT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    }
    upper_bias = config.search_variant in {
        PlannerSearchVariant.UPPER_LEFT,
        PlannerSearchVariant.UPPER_RIGHT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    }

    model.add_decision_strategy(
        x_vars,
        cp_model.CHOOSE_FIRST,
        cp_model.SELECT_MAX_VALUE if right_bias else cp_model.SELECT_MIN_VALUE,
    )
    model.add_decision_strategy(
        y_vars,
        cp_model.CHOOSE_FIRST,
        cp_model.SELECT_MAX_VALUE if upper_bias else cp_model.SELECT_MIN_VALUE,
    )
    model.add_decision_strategy(
        size_vars,
        cp_model.CHOOSE_FIRST,
        cp_model.SELECT_MIN_VALUE,
    )

    solver = cp_model.CpSolver()
    wall_budget_seconds = config.max_time_ms / 1000.0
    if config.residential_planning.enabled:
        # Residential production quality must not depend on host load at a
        # short wall-clock cutoff. The primary search-work limits are
        # deterministic (single worker, fixed seed, deterministic time and
        # conflict budget). A much larger wall-clock cap remains only as an
        # emergency operational failsafe.
        deterministic_budget = max(20.0, wall_budget_seconds * 4.0)
        solver.parameters.max_deterministic_time = deterministic_budget
        solver.parameters.max_time_in_seconds = max(
            60.0,
            deterministic_budget * 3.0,
        )
    else:
        solver.parameters.max_time_in_seconds = wall_budget_seconds
    solver.parameters.max_number_of_conflicts = config.max_conflicts
    solver.parameters.random_seed = config.random_seed
    solver.parameters.num_search_workers = 1
    # The legacy planner retains its explicit deterministic branch order.
    # Residential planning has a materially richer objective model
    # (occupancy, room-area balance, compactness and topology). Forcing
    # positions first and minimum room sizes last is hostile to that model
    # and can exhaust the time budget before finding a useful incumbent.
    #
    # AUTOMATIC_SEARCH remains reproducible here because the planner keeps
    # one search worker and the configured deterministic random seed.
    solver.parameters.search_branching = (
        cp_model.AUTOMATIC_SEARCH if config.residential_planning.enabled else cp_model.FIXED_SEARCH
    )
    solver.parameters.log_search_progress = False

    raw_status = solver.solve(model)
    status = _status(raw_status)
    metadata = _metadata(problem, config)
    if status not in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
        return PlannerResult(
            status=status,
            metadata=metadata,
            notices=tuple(notices),
        ).with_content_hash()

    floor_index = problem.available_floor_indices[0]
    placements = []
    for room in ordered_rooms:
        rv = room_vars[room.id]
        width_mm = solver.value(rv.width) * step
        depth_mm = solver.value(rv.depth) * step
        placements.append(
            RoomPlacement(
                room_instance_id=room.id,
                room_type=room.room_type,
                floor_index=floor_index,
                x_mm=bounds.min_x_mm + solver.value(rv.x) * step,
                y_mm=bounds.min_y_mm + solver.value(rv.y) * step,
                width_mm=width_mm,
                depth_mm=depth_mm,
                area_mm2=width_mm * depth_mm,
            )
        )

    contributions = []
    for term in penalty_terms:
        penalty = int(solver.value(term.expression))
        contributions.append(
            ObjectiveContribution(
                constraint_id=term.constraint_id,
                kind=term.kind,
                penalty_units=penalty,
                weight=term.weight,
                weighted_penalty=penalty * term.weight,
            )
        )
    contributions.sort(key=lambda item: str(item.constraint_id))
    total = sum(item.weighted_penalty for item in contributions)
    return PlannerResult(
        status=status,
        metadata=metadata,
        placements=tuple(placements),
        objective_penalty=total,
        objective_contributions=tuple(contributions),
        notices=tuple(sorted(notices, key=lambda item: (item.code, str(item.constraint_id)))),
    ).with_content_hash()


def _metadata(problem: CompiledConstraintProblem, config: PlannerConfig) -> SolverRunMetadata:
    problem_hash = problem.content_hash or problem.compute_content_hash()
    return SolverRunMetadata(
        solver_version=version("ortools"),
        problem_hash=problem_hash,
        config=config,
    )


def _empty_result(
    problem: CompiledConstraintProblem,
    config: PlannerConfig,
    status: PlannerStatus,
    *,
    notice: str,
) -> PlannerResult:
    return PlannerResult(
        status=status,
        metadata=_metadata(problem, config),
        notices=(
            PlannerNotice(
                code="SOLVER_LATTICE_INFEASIBLE",
                severity=PlannerNoticeSeverity.WARNING,
                message=notice,
            ),
        ),
    ).with_content_hash()
