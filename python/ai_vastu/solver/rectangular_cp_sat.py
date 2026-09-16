from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import Any

from ortools.sat.python import cp_model

from ai_vastu.constraints import (
    AdjacencyAvoidanceObjective,
    AdjacencyPreferenceObjective,
    AdjacencyProhibitionConstraint,
    AspectRatioConstraint,
    AvailableFloorsConstraint,
    CompiledConstraintProblem,
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
from ai_vastu.plan_schema import IntPolygon

from .errors import SolverModelError, UnsupportedSolverProblemError
from .models import (
    ObjectiveContribution,
    PlannerConfig,
    PlannerNotice,
    PlannerNoticeSeverity,
    PlannerResult,
    PlannerStatus,
    RoomPlacement,
    SolverRunMetadata,
)


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
    x_interval: Any
    y_interval: Any


@dataclass(frozen=True)
class _PenaltyTerm:
    constraint_id: Any
    kind: str
    weight: int
    expression: Any


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


def _adjacency_pair_penalty(
    model: Any,
    source: _RoomVars,
    target: _RoomVars,
    *,
    config: PlannerConfig,
    buildable_width_cells: int,
    buildable_depth_cells: int,
    objective: AdjacencyPreferenceObjective,
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
    total_upper = (
        (buildable_width_cells + buildable_depth_cells) * config.solver_step_mm
        + (objective.min_shared_length_mm or 0)
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
        raise UnsupportedSolverProblemError(
            "Phase 7 planner supports exactly one available floor."
        )
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
    hard_by_room = _room_constraint_index(problem)
    ordered_rooms = tuple(sorted(problem.room_instances, key=lambda item: str(item.id)))

    for room in ordered_rooms:
        constraints = hard_by_room.get(room.id, [])
        if any(isinstance(item, AdjacencyProhibitionConstraint) for item in constraints):
            raise UnsupportedSolverProblemError(
                "Hard adjacency prohibitions are not yet modeled by the Phase 7 planner."
            )

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
            else:
                raise UnsupportedSolverProblemError(
                    f"Unsupported hard constraint in Phase 7: {constraint.kind}."
                )

        min_w_cells = (min_width_mm + step - 1) // step
        min_d_cells = (min_depth_mm + step - 1) // step
        max_w_cells = min(width_cells, max_width_mm // step)
        max_d_cells = min(depth_cells, max_depth_mm // step)
        if min_w_cells > max_w_cells or min_d_cells > max_d_cells:
            return _empty_result(
                problem,
                config,
                PlannerStatus.INFEASIBLE,
                notice="Room dimension bounds contain no value on the configured solver lattice.",
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
        step2 = step * step
        model.add(area_cells2 * step2 >= min_area_mm2)
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
            x_interval=x_interval,
            y_interval=y_interval,
        )

    model.add_no_overlap_2d(
        [room_vars[room.id].x_interval for room in ordered_rooms],
        [room_vars[room.id].y_interval for room in ordered_rooms],
    )

    notices: list[PlannerNotice] = []
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
                upper = (bounds.width_mm + bounds.depth_mm) + (
                    objective.min_shared_length_mm or 0
                )
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
                    "Floor preference is trivially satisfied by the Phase 7 "
                    "single-floor domain."
                ),
                constraint_id=objective.id,
                room_instance_id=objective.room_instance_id,
            )
        elif isinstance(objective, PreferredAreaObjective):
            _append_notice(
                notices,
                code="SOFT_OBJECTIVE_NOT_YET_OPTIMIZED",
                message=(
                    "Preferred area is preserved in the compiled problem but not "
                    "optimized in Phase 7."
                ),
                constraint_id=objective.id,
                room_instance_id=objective.room_instance_id,
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

    if penalty_terms:
        model.minimize(sum(term.expression * term.weight for term in penalty_terms))

    decision_vars: list[Any] = []
    for room in ordered_rooms:
        rv = room_vars[room.id]
        decision_vars.extend([rv.x, rv.y, rv.width, rv.depth])
    model.add_decision_strategy(decision_vars, cp_model.CHOOSE_FIRST, cp_model.SELECT_MIN_VALUE)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.max_time_ms / 1000.0
    solver.parameters.max_number_of_conflicts = config.max_conflicts
    solver.parameters.random_seed = config.random_seed
    solver.parameters.num_search_workers = 1
    solver.parameters.search_branching = cp_model.FIXED_SEARCH
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
