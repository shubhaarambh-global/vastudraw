from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import UUID, uuid5

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryError,
    ArchitecturalGeometryRequest,
    ArchitecturalGeometryResult,
    OpeningBuildRequest,
    StairBuildRequest,
    VerticalArchitecturePlanningError,
    VerticalCorePlan,
    build_architectural_geometry,
    plan_vertical_architecture,
    validate_circulation,
    validate_whole_building,
)
from ai_vastu.constraints import (
    ConstraintCompilerError,
    ConstraintCompilerInput,
    compile_constraints,
)
from ai_vastu.plan_schema import (
    DoorSwing,
    OpeningKind,
    RoomGeometry,
    RoomRequirement,
    RoomType,
    Wall,
    WallCategory,
)
from ai_vastu.solver import (
    PlannerBoundarySide,
    PlannerError,
    PlannerStatus,
    solve_rectangular_problem,
)
from ai_vastu.validation import (
    ArchitecturalValidationRequest,
    validate_architectural_geometry,
)

from .errors import CirculationGenerationError, GenerationInputError
from .models import (
    ArchitecturalGenerationRequest,
    ArchitecturalGenerationResult,
    FloorGenerationResult,
    GenerationDisposition,
)


def _localize_floor_requirements(
    requirements: tuple[RoomRequirement, ...],
) -> tuple[RoomRequirement, ...]:
    present = {item.room_type for item in requirements}
    localized = []
    for requirement in requirements:
        localized.append(
            requirement.model_copy(
                update={
                    "adjacency_preferences": tuple(
                        item
                        for item in requirement.adjacency_preferences
                        if item.target_room_type in present
                    )
                }
            )
        )
    return tuple(localized)


@dataclass(frozen=True, slots=True)
class _CirculationWall:
    wall: Wall
    adjacent_room_ids: tuple[UUID, ...]


def _wall_length_mm(wall: Wall) -> int:
    return abs(wall.axis.end.x_mm - wall.axis.start.x_mm) + abs(
        wall.axis.end.y_mm - wall.axis.start.y_mm
    )


def _wall_sort_key(wall: Wall) -> tuple[int, int, int, int, str]:
    return (
        wall.axis.start.x_mm,
        wall.axis.start.y_mm,
        wall.axis.end.x_mm,
        wall.axis.end.y_mm,
        str(wall.id),
    )


def _edge_signature(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> tuple[str, int, int, int] | None:
    if y1 == y2:
        return ("H", y1, min(x1, x2), max(x1, x2))
    if x1 == x2:
        return ("V", x1, min(y1, y2), max(y1, y2))
    return None


def _overlap_length(first: tuple[int, int], second: tuple[int, int]) -> int:
    return max(0, min(first[1], second[1]) - max(first[0], second[0]))


def _wall_on_boundary_side(
    wall: Wall,
    request: ArchitecturalGenerationRequest,
    side: PlannerBoundarySide,
) -> bool:
    points = request.buildable_area.polygon.outer
    xs = [point.x_mm for point in points]
    ys = [point.y_mm for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    step = request.planner_config.solver_step_mm
    lattice_max_x = min_x + ((max_x - min_x) // step) * step
    lattice_max_y = min_y + ((max_y - min_y) // step) * step

    if side is PlannerBoundarySide.SOUTH:
        return wall.axis.start.y_mm == min_y and wall.axis.end.y_mm == min_y
    if side is PlannerBoundarySide.EAST:
        return wall.axis.start.x_mm == lattice_max_x and wall.axis.end.x_mm == lattice_max_x
    if side is PlannerBoundarySide.NORTH:
        return wall.axis.start.y_mm == lattice_max_y and wall.axis.end.y_mm == lattice_max_y
    return wall.axis.start.x_mm == min_x and wall.axis.end.x_mm == min_x


def _adjacent_room_ids(wall: Wall, rooms: tuple[RoomGeometry, ...]) -> tuple[UUID, ...]:
    wall_edge = _edge_signature(
        wall.axis.start.x_mm,
        wall.axis.start.y_mm,
        wall.axis.end.x_mm,
        wall.axis.end.y_mm,
    )
    if wall_edge is None:
        return ()

    orientation, fixed, lo, hi = wall_edge
    adjacent: list[UUID] = []
    for room in rooms:
        points = room.polygon.outer
        for index, start in enumerate(points):
            end = points[(index + 1) % len(points)]
            edge = _edge_signature(
                start.x_mm,
                start.y_mm,
                end.x_mm,
                end.y_mm,
            )
            if edge is None:
                continue
            edge_orientation, edge_fixed, edge_lo, edge_hi = edge
            if edge_orientation != orientation or edge_fixed != fixed:
                continue
            if _overlap_length((lo, hi), (edge_lo, edge_hi)) > 0:
                adjacent.append(room.id)
                break

    return tuple(sorted(set(adjacent), key=str))


_ACCESS_PRIORITY = {
    "foyer": 0,
    "verandah": 1,
    "lobby": 1,
    "living": 2,
    "drawing": 3,
    "family_lounge": 4,
    "dining": 5,
    "kitchen": 6,
    "parking": 7,
    "garage": 8,
    "bedroom": 9,
    "master_bedroom": 9,
    "parents_bedroom": 9,
    "guest_bedroom": 9,
    "children_bedroom": 9,
}

_SANITARY_ROOM_TYPES = frozenset(
    {
        "attached_toilet",
        "common_toilet",
        "powder_room",
        "bath",
        "servant_toilet",
    }
)


def _interior_circulation_anchor(
    rooms: tuple[RoomGeometry, ...],
    *,
    core_plan: VerticalCorePlan | None,
) -> UUID:
    if core_plan is not None:
        staircase_rooms = tuple(
            room for room in rooms if room.room_type is RoomType.STAIRCASE
        )
        if len(staircase_rooms) != 1:
            raise CirculationGenerationError(
                "[VERTICAL_CORE_MISSING] An upper-floor circulation graph requires "
                "exactly one staircase anchor."
            )
        return staircase_rooms[0].id
    return min(
        rooms,
        key=lambda room: (_ACCESS_PRIORITY.get(room.room_type.value, 50), str(room.id)),
    ).id


def _centered_opening(
    wall: Wall,
    *,
    width_mm: int,
    height_mm: int,
) -> OpeningBuildRequest:
    length = _wall_length_mm(wall)
    return OpeningBuildRequest(
        wall_id=wall.id,
        kind=OpeningKind.DOOR,
        offset_from_wall_start_mm=(length - width_mm) // 2,
        width_mm=width_mm,
        height_mm=height_mm,
        sill_height_mm=0,
        hinge=None,
        swing=DoorSwing.NONE,
    )


def _synthesize_circulation_openings(
    geometry: ArchitecturalGeometryResult,
    request: ArchitecturalGenerationRequest,
) -> tuple[OpeningBuildRequest, ...]:
    floor = geometry.floor
    rooms = tuple(floor.rooms)
    if not rooms:
        raise GenerationInputError("Auto circulation requires at least one generated room.")

    config = request.circulation_config
    room_index = {room.id: room for room in rooms}
    walls = tuple(
        _CirculationWall(
            wall=wall,
            adjacent_room_ids=_adjacent_room_ids(wall, rooms),
        )
        for wall in floor.walls
    )

    external_candidates = [
        candidate
        for candidate in walls
        if candidate.wall.category is WallCategory.EXTERNAL
        and len(candidate.adjacent_room_ids) == 1
        and _wall_length_mm(candidate.wall)
        >= config.external_door_width_mm + 2 * config.edge_margin_mm
    ]

    planning = request.planner_config.residential_planning
    if planning.enabled and planning.entrance_boundary_side is not None:
        external_candidates = [
            candidate
            for candidate in external_candidates
            if _wall_on_boundary_side(
                candidate.wall,
                request,
                planning.entrance_boundary_side,
            )
        ]

    if not external_candidates and config.require_external_entry:
        raise GenerationInputError(
            "Auto circulation could not place an exterior access door on the "
            "required entrance boundary."
        )

    def external_key(candidate: _CirculationWall) -> tuple[int, tuple[int, int, int, int, str]]:
        room = room_index[candidate.adjacent_room_ids[0]]
        priority = _ACCESS_PRIORITY.get(room.room_type.value, 50)
        return (priority, _wall_sort_key(candidate.wall))

    openings: list[OpeningBuildRequest] = []
    if config.require_external_entry and external_candidates:
        exterior = min(external_candidates, key=external_key)
        root_room_id = exterior.adjacent_room_ids[0]
        openings.append(
            _centered_opening(
                exterior.wall,
                width_mm=config.external_door_width_mm,
                height_mm=config.door_height_mm,
            )
        )
    else:
        root_room_id = _interior_circulation_anchor(
            rooms,
            core_plan=request.vertical_core_plan,
        )

    internal_candidates = [
        candidate
        for candidate in walls
        if candidate.wall.category is WallCategory.INTERNAL
        and len(candidate.adjacent_room_ids) == 2
        and _wall_length_mm(candidate.wall)
        >= config.internal_door_width_mm + 2 * config.edge_margin_mm
    ]
    internal_candidates.sort(
        key=lambda candidate: (
            _wall_sort_key(candidate.wall),
            tuple(str(room_id) for room_id in candidate.adjacent_room_ids),
        )
    )

    required_room_ids = {
        room_id
        for room_id, room in room_index.items()
        if room.room_type.value not in {"parking", "garage"}
    }
    sanitary_room_ids = {
        room_id
        for room_id, room in room_index.items()
        if room.room_type.value in _SANITARY_ROOM_TYPES
    }
    visited: set[UUID] = {root_room_id}

    def add_crossing(candidates: list[_CirculationWall]) -> bool:
        crossing = [
            candidate
            for candidate in candidates
            if (
                (candidate.adjacent_room_ids[0] in visited)
                != (candidate.adjacent_room_ids[1] in visited)
            )
        ]
        if not crossing:
            return False
        chosen = crossing[0]
        openings.append(
            _centered_opening(
                chosen.wall,
                width_mm=config.internal_door_width_mm,
                height_mm=config.door_height_mm,
            )
        )
        visited.update(chosen.adjacent_room_ids)
        return True

    # Establish the public/private/service spine without using a sanitary
    # room as a shortcut between otherwise unrelated rooms.
    non_sanitary = [
        candidate
        for candidate in internal_candidates
        if all(room_id not in sanitary_room_ids for room_id in candidate.adjacent_room_ids)
    ]
    while required_room_ids - visited - sanitary_room_ids:
        if not add_crossing(non_sanitary):
            missing = ", ".join(
                sorted(str(room_id) for room_id in required_room_ids - visited - sanitary_room_ids)
            )
            raise CirculationGenerationError(
                "[CIRCULATION_DISCONNECTED] Auto circulation could not connect "
                f"required non-sanitary rooms. Unreachable room IDs: {missing}."
            )

    # Sanitary rooms may be leaves on the circulation graph, but never transit
    # nodes. This also prevents a toilet door from becoming the only route to a
    # bedroom, kitchen, or passage.
    sanitary_leaves = [
        candidate
        for candidate in internal_candidates
        if (
            (candidate.adjacent_room_ids[0] in sanitary_room_ids)
            != (candidate.adjacent_room_ids[1] in sanitary_room_ids)
        )
    ]
    while sanitary_room_ids - visited:
        if not add_crossing(sanitary_leaves):
            missing = ", ".join(sorted(str(room_id) for room_id in sanitary_room_ids - visited))
            raise CirculationGenerationError(
                "[CIRCULATION_DISCONNECTED] Sanitary rooms must be reachable as "
                f"leaves, not transit rooms. Unreachable room IDs: {missing}."
            )

    if required_room_ids - visited:
        missing = ", ".join(sorted(str(room_id) for room_id in required_room_ids - visited))
        raise CirculationGenerationError(
            "[CIRCULATION_DISCONNECTED] Auto circulation left required rooms "
            f"unreachable. Unreachable room IDs: {missing}."
        )

    return tuple(openings)


def _generate_single_floor_plan(
    request: ArchitecturalGenerationRequest,
) -> ArchitecturalGenerationResult:
    """Run the deterministic architectural pipeline without inventing Vastu semantics.

    Phase 16 deliberately orchestrates only the already-validated architectural engine.
    Vastu rules remain outside this workflow until Vastu Specification v1 is reviewed,
    frozen and cryptographically pinned.
    """

    try:
        problem = compile_constraints(
            ConstraintCompilerInput(
                buildable_area=request.buildable_area,
                available_floor_indices=(request.floor_index,),
                room_requirements=request.room_requirements,
                assumptions=request.assumptions,
                instance_namespace=f"floor:{request.floor_index}",
            )
        )
        planner_result = solve_rectangular_problem(
            problem,
            config=request.planner_config,
        )
    except (ConstraintCompilerError, PlannerError, ValueError) as exc:
        raise GenerationInputError(str(exc)) from exc

    if planner_result.status not in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
        return ArchitecturalGenerationResult(
            disposition=GenerationDisposition.UNSOLVED,
            problem=problem,
            planner_result=planner_result,
        ).with_content_hash()

    try:
        if request.circulation_config.auto_generate and request.openings:
            raise GenerationInputError(
                "Auto circulation and explicit opening requests cannot be combined."
            )
        if request.circulation_config.auto_generate and request.swing_contexts:
            raise GenerationInputError("Auto circulation does not accept explicit swing contexts.")

        stair_requests = request.stairs
        if request.vertical_core_plan is not None:
            stair_rooms = tuple(
                room for room in problem.room_instances if room.room_type is RoomType.STAIRCASE
            )
            if len(stair_rooms) != 1:
                raise GenerationInputError(
                    "VERTICAL_CORE_INVALID: every served floor requires exactly one "
                    "staircase room instance."
                )
            if stair_requests:
                raise GenerationInputError(
                    "VERTICAL_CORE_AMBIGUOUS: deterministic building-core stairs cannot "
                    "be combined with explicit per-floor stair geometry requests."
                )
            core = request.vertical_core_plan
            stair_requests = (
                StairBuildRequest(
                    room_instance_id=stair_rooms[0].id,
                    stair_type=core.stair_type,
                    width_mm=core.width_mm,
                    riser_mm=core.riser_mm,
                    tread_mm=core.tread_mm,
                    number_of_risers=core.number_of_risers,
                    floor_height_mm=core.floor_height_mm,
                    landing_depth_mm=core.landing_depth_mm,
                    direction_udeg=core.direction_udeg,
                    headroom_mm=core.headroom_mm,
                ),
            )

        geometry_request = ArchitecturalGeometryRequest(
            problem=problem,
            planner_result=planner_result,
            floor_id=request.floor_id,
            floor_name=request.floor_name,
            elevation_mm=request.elevation_mm,
            floor_to_floor_mm=request.floor_to_floor_mm,
            wall_config=request.wall_config,
            openings=request.openings,
            stairs=stair_requests,
        )
        geometry_result = build_architectural_geometry(geometry_request)

        if request.circulation_config.auto_generate:
            generated_openings = _synthesize_circulation_openings(
                geometry_result,
                request,
            )
            geometry_result = build_architectural_geometry(
                geometry_request.model_copy(update={"openings": generated_openings})
            )

            circulation = validate_circulation(
                geometry_result.floor,
                internal_door_width_mm=request.circulation_config.internal_door_width_mm,
                edge_margin_mm=request.circulation_config.edge_margin_mm,
                require_external_entry=request.circulation_config.require_external_entry,
                anchor_room_ids=(
                    _interior_circulation_anchor(
                        geometry_result.floor.rooms,
                        core_plan=request.vertical_core_plan,
                    ),
                ) if not request.circulation_config.require_external_entry else (),
            )
            if not circulation.accepted:
                raise CirculationGenerationError(
                    f"[{circulation.reason_code or 'CIRCULATION_INVALID'}] "
                    f"{circulation.message}"
                )

        validation_result = validate_architectural_geometry(
            ArchitecturalValidationRequest(
                plot_boundary=request.plot_boundary,
                problem=problem,
                geometry=geometry_result,
                config=request.validation_config,
                swing_contexts=request.swing_contexts,
                circulation_anchor_room_ids=(
                    _interior_circulation_anchor(
                        geometry_result.floor.rooms,
                        core_plan=request.vertical_core_plan,
                    ),
                ) if not request.circulation_config.require_external_entry else (),
            )
        )
    except (ArchitecturalGeometryError, ValueError) as exc:
        raise GenerationInputError(str(exc)) from exc

    disposition = (
        GenerationDisposition.ACCEPTED
        if validation_result.report.valid
        else GenerationDisposition.REJECTED
    )
    return ArchitecturalGenerationResult(
        disposition=disposition,
        problem=problem,
        planner_result=planner_result,
        geometry_result=geometry_result,
        validation_result=validation_result,
    ).with_content_hash()


def generate_architectural_plan(
    request: ArchitecturalGenerationRequest,
) -> ArchitecturalGenerationResult:
    """Generate one deterministic building, solving each floor independently."""

    if request.floor_count == 1:
        return _generate_single_floor_plan(request)

    if len(request.floor_requirements) != request.floor_count:
        raise GenerationInputError(
            "PROGRAM_DISTRIBUTION_FAILURE: one room-requirement partition is required per floor."
        )

    if request.stairs:
        raise GenerationInputError(
            "VERTICAL_CORE_AMBIGUOUS: multi-floor generation derives canonical stair "
            "geometry from one building-level core plan."
        )

    try:
        core_plan: VerticalCorePlan = request.vertical_core_plan or plan_vertical_architecture(
            seed_id=request.floor_id,
            buildable_area=request.buildable_area,
            floor_buildable_areas=request.floor_buildable_areas,
            floor_count=request.floor_count,
            floor_height_mm=request.floor_to_floor_mm,
            solver_step_mm=request.planner_config.solver_step_mm,
            search_variant=request.planner_config.search_variant,
        )
    except VerticalArchitecturePlanningError as exc:
        raise GenerationInputError(str(exc)) from exc

    floor_results: list[FloorGenerationResult] = []
    for floor_index, requirements in enumerate(request.floor_requirements):
        localized_requirements = _localize_floor_requirements(requirements)
        floor_request = request.model_copy(
            update={
                "room_requirements": localized_requirements,
                "floor_requirements": (),
                "floor_buildable_areas": (),
                "floor_count": 1,
                "floor_index": floor_index,
                "floor_id": request.floor_id
                if floor_index == 0
                else uuid5(request.floor_id, f"floor:{floor_index}"),
                "floor_name": "Ground Floor" if floor_index == 0 else f"Floor {floor_index}",
                "elevation_mm": request.elevation_mm
                + floor_index * request.floor_to_floor_mm,
                "buildable_area": (
                    request.floor_buildable_areas[floor_index]
                    if request.floor_buildable_areas
                    else request.buildable_area
                ),
                "vertical_circulation_status": "PLANNED",
                "vertical_core_plan": core_plan,
                "planner_config": request.planner_config.model_copy(
                    update={
                        "residential_planning": (
                            request.planner_config.residential_planning.model_copy(
                            update={
                                "require_entrance_boundary_access": floor_index == 0,
                                "require_road_connected_parking": floor_index == 0,
                                "require_horizontal_circulation": request.floor_count > 1,
                                "vertical_core_footprint": core_plan.footprint,
                                "wet_stack_anchor": core_plan.wet_stack_anchor,
                            }
                            )
                        ),
                    }
                ),
                "validation_config": request.validation_config.model_copy(
                    update={"require_exterior_access": floor_index == 0}
                ),
                "circulation_config": request.circulation_config.model_copy(
                    update={"require_external_entry": floor_index == 0}
                ),
            }
        )
        result = _generate_single_floor_plan(floor_request)
        floor_results.append(
            FloorGenerationResult(
                floor_index=floor_index,
                problem=result.problem,
                planner_result=result.planner_result,
                geometry_result=result.geometry_result,
                validation_result=result.validation_result,
            )
        )

    first = floor_results[0]
    all_feasible = all(
        item.planner_result.status in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE)
        for item in floor_results
    )
    all_floor_valid = all(
        item.geometry_result is not None
        and item.validation_result is not None
        and item.validation_result.report.valid
        for item in floor_results
    )
    building_validation = None
    if all_feasible:
        floors = tuple(
            item.geometry_result.floor
            for item in floor_results
            if item.geometry_result is not None
        )
        expected_program = Counter(
            requirement.room_type.value
            for requirement in request.room_requirements
            for _ in range(requirement.quantity)
        )
        building_validation = validate_whole_building(
            floors=floors,
            expected_floor_count=request.floor_count,
            expected_program=expected_program,
            core_plan=core_plan,
            internal_door_width_mm=request.circulation_config.internal_door_width_mm,
            edge_margin_mm=request.circulation_config.edge_margin_mm,
        )
    disposition = (
        GenerationDisposition.ACCEPTED
        if all_feasible
        and all_floor_valid
        and building_validation is not None
        and building_validation.accepted
        else GenerationDisposition.REJECTED
        if all_feasible
        else GenerationDisposition.UNSOLVED
    )
    return ArchitecturalGenerationResult(
        disposition=disposition,
        problem=first.problem,
        planner_result=first.planner_result,
        geometry_result=first.geometry_result,
        validation_result=first.validation_result,
        floor_results=tuple(floor_results),
        vertical_circulation_status=(
            "VALIDATED"
            if building_validation is not None and building_validation.accepted
            else "PLANNED"
        ),
        vertical_core_plan=core_plan,
        building_validation=building_validation,
    ).with_content_hash()
