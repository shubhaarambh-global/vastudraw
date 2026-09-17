from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryError,
    ArchitecturalGeometryRequest,
    ArchitecturalGeometryResult,
    OpeningBuildRequest,
    build_architectural_geometry,
)
from ai_vastu.constraints import (
    ConstraintCompilerError,
    ConstraintCompilerInput,
    compile_constraints,
)
from ai_vastu.plan_schema import DoorSwing, OpeningKind, RoomGeometry, Wall, WallCategory
from ai_vastu.solver import PlannerError, PlannerStatus, solve_rectangular_problem
from ai_vastu.validation import (
    ArchitecturalValidationRequest,
    validate_architectural_geometry,
)

from .errors import GenerationInputError
from .models import (
    ArchitecturalGenerationRequest,
    ArchitecturalGenerationResult,
    GenerationDisposition,
)


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
    "living": 0,
    "drawing": 1,
    "foyer": 2,
    "verandah": 3,
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
    if not external_candidates:
        raise GenerationInputError(
            "Auto circulation could not place an exterior access door on any generated wall."
        )

    def external_key(candidate: _CirculationWall) -> tuple[int, tuple[int, int, int, int, str]]:
        room = room_index[candidate.adjacent_room_ids[0]]
        priority = _ACCESS_PRIORITY.get(room.room_type.value, 50)
        return (priority, _wall_sort_key(candidate.wall))

    exterior = min(external_candidates, key=external_key)
    root_room_id = exterior.adjacent_room_ids[0]
    openings: list[OpeningBuildRequest] = [
        _centered_opening(
            exterior.wall,
            width_mm=config.external_door_width_mm,
            height_mm=config.door_height_mm,
        )
    ]

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

    visited: set[UUID] = {root_room_id}
    all_room_ids = set(room_index)
    while visited != all_room_ids:
        crossing = [
            candidate
            for candidate in internal_candidates
            if (
                (candidate.adjacent_room_ids[0] in visited)
                != (candidate.adjacent_room_ids[1] in visited)
            )
        ]
        if not crossing:
            missing = ", ".join(sorted(str(room_id) for room_id in all_room_ids - visited))
            raise GenerationInputError(
                "Auto circulation could not connect every generated room with the "
                f"available shared wall segments. Unreachable room IDs: {missing}."
            )

        chosen = crossing[0]
        openings.append(
            _centered_opening(
                chosen.wall,
                width_mm=config.internal_door_width_mm,
                height_mm=config.door_height_mm,
            )
        )
        for room_id in chosen.adjacent_room_ids:
            visited.add(room_id)

    return tuple(openings)


def generate_architectural_plan(
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

        geometry_request = ArchitecturalGeometryRequest(
            problem=problem,
            planner_result=planner_result,
            floor_id=request.floor_id,
            floor_name=request.floor_name,
            elevation_mm=request.elevation_mm,
            floor_to_floor_mm=request.floor_to_floor_mm,
            wall_config=request.wall_config,
            openings=request.openings,
            stairs=request.stairs,
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

        validation_result = validate_architectural_geometry(
            ArchitecturalValidationRequest(
                plot_boundary=request.plot_boundary,
                problem=problem,
                geometry=geometry_result,
                config=request.validation_config,
                swing_contexts=request.swing_contexts,
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
