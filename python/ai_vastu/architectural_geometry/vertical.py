from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from enum import StrEnum
from itertools import pairwise
from typing import Annotated, Literal
from uuid import UUID, uuid5

from pydantic import Field, model_validator

from ai_vastu.plan_schema import (
    BuildableArea,
    Floor,
    IntPoint,
    IntPolygon,
    RoomGeometry,
    RoomType,
    StairType,
)
from ai_vastu.plan_schema.base import FrozenModel
from ai_vastu.plan_schema.models import EntityId
from ai_vastu.solver import PlannerSearchVariant

from .circulation import validate_circulation

_CORE_NAMESPACE = UUID("2e94a604-bcb4-5dd2-830a-649b355145a2")
_VEHICLE_ROOM_TYPES = frozenset({RoomType.PARKING, RoomType.GARAGE})
_SANITARY_ROOM_TYPES = frozenset(
    {
        RoomType.ATTACHED_TOILET,
        RoomType.COMMON_TOILET,
        RoomType.POWDER_ROOM,
        RoomType.BATH,
        RoomType.SERVANT_TOILET,
    }
)
_WET_ROOM_TYPES = frozenset(
    {
        *_SANITARY_ROOM_TYPES,
        RoomType.KITCHEN,
        RoomType.UTILITY,
        RoomType.LAUNDRY,
    }
)
_CIRCULATION_CAPABLE_ROOM_TYPES = frozenset(
    {
        RoomType.LOBBY,
        RoomType.CORRIDOR,
        RoomType.FOYER,
        RoomType.LIVING,
        RoomType.DRAWING,
        RoomType.DINING,
        RoomType.FAMILY_LOUNGE,
        RoomType.VERANDAH,
    }
)
_CORE_WIDTH_MM = 2_300
_CORE_DEPTH_MM = 3_500
_STAIR_WIDTH_MM = 1_000
_STAIR_TREAD_MM = 270
_STAIR_LANDING_MM = 1_000
_STAIR_HEADROOM_MM = 2_100
_WET_PROXIMITY_MM = 3_000
BoundedMessage = Annotated[str, Field(min_length=1, max_length=500)]


class VerticalArchitecturePlanningError(ValueError):
    pass


class BuildingDiagnosticSeverity(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class WetStackRelationship(StrEnum):
    ALIGNED = "ALIGNED"
    PROXIMATE = "PROXIMATE"
    DISPERSED = "DISPERSED"


class VerticalCorePlan(FrozenModel):
    core_id: EntityId
    footprint: IntPolygon
    served_floor_indices: tuple[int, ...]
    stair_type: StairType = StairType.DOG_LEGGED
    width_mm: int
    riser_mm: int
    tread_mm: int
    number_of_risers: int
    floor_height_mm: int
    landing_depth_mm: int
    direction_udeg: int
    headroom_mm: int
    wet_stack_anchor: IntPoint

    @model_validator(mode="after")
    def validate_core(self) -> VerticalCorePlan:
        if self.served_floor_indices != tuple(range(len(self.served_floor_indices))):
            raise ValueError("Vertical core must serve consecutive floors from index 0.")
        if len(self.served_floor_indices) < 2:
            raise ValueError("Vertical core planning requires at least two served floors.")
        if self.riser_mm * self.number_of_risers != self.floor_height_mm:
            raise ValueError("Vertical core risers must close the floor-to-floor height exactly.")
        return self


class WetStackPair(FrozenModel):
    lower_floor_index: int
    upper_floor_index: int
    lower_room_id: EntityId
    upper_room_id: EntityId
    lower_room_type: RoomType
    upper_room_type: RoomType
    center_distance_mm: int
    relationship: WetStackRelationship


class WetStackEvaluation(FrozenModel):
    completed: Literal[True] = True
    pairs: tuple[WetStackPair, ...] = ()
    unpaired_upper_room_ids: tuple[EntityId, ...] = ()
    aligned_count: int = 0
    proximate_count: int = 0
    dispersed_count: int = 0
    score_basis_points: int = 10_000


class BuildingRoomNode(FrozenModel):
    floor_index: int
    room_id: EntityId


class VerticalTransfer(FrozenModel):
    lower_floor_index: int
    upper_floor_index: int
    lower_room_id: EntityId
    upper_room_id: EntityId


class WholeBuildingCirculationGraph(FrozenModel):
    entry_nodes: tuple[BuildingRoomNode, ...] = ()
    required_nodes: tuple[BuildingRoomNode, ...] = ()
    reachable_nodes: tuple[BuildingRoomNode, ...] = ()
    disconnected_nodes: tuple[BuildingRoomNode, ...] = ()
    vertical_transfers: tuple[VerticalTransfer, ...] = ()


class BuildingDiagnostic(FrozenModel):
    code: str
    severity: BuildingDiagnosticSeverity
    message: BoundedMessage
    floor_indices: tuple[int, ...] = ()
    entity_refs: tuple[EntityId, ...] = ()


class WholeBuildingValidation(FrozenModel):
    accepted: bool
    diagnostics: tuple[BuildingDiagnostic, ...]
    circulation: WholeBuildingCirculationGraph
    wet_stack: WetStackEvaluation

    @model_validator(mode="after")
    def validate_disposition(self) -> WholeBuildingValidation:
        has_errors = any(
            item.severity is BuildingDiagnosticSeverity.ERROR for item in self.diagnostics
        )
        if self.accepted == has_errors:
            raise ValueError("Whole-building acceptance must exactly reflect error diagnostics.")
        return self


def _polygon_bounds(polygon: IntPolygon) -> tuple[int, int, int, int]:
    xs = {point.x_mm for point in polygon.outer}
    ys = {point.y_mm for point in polygon.outer}
    if len(xs) != 2 or len(ys) != 2 or len(polygon.outer) != 4:
        raise VerticalArchitecturePlanningError(
            "Vertical-core planning currently requires rectangular buildable footprints."
        )
    return min(xs), min(ys), max(xs), max(ys)


def _rectangle(x0: int, y0: int, width: int, depth: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x0, y_mm=y0),
            IntPoint(x_mm=x0 + width, y_mm=y0),
            IntPoint(x_mm=x0 + width, y_mm=y0 + depth),
            IntPoint(x_mm=x0, y_mm=y0 + depth),
        )
    )


def _ceil_to_step(value: int, step: int) -> int:
    return ((value + step - 1) // step) * step


def _floor_to_step(value: int, step: int) -> int:
    return (value // step) * step


def _stair_riser_geometry(floor_height_mm: int) -> tuple[int, int]:
    candidates = []
    for count in range(14, 23):
        if floor_height_mm % count:
            continue
        riser = floor_height_mm // count
        if 150 <= riser <= 190:
            candidates.append((abs(riser - 170), count, riser))
    if not candidates:
        raise VerticalArchitecturePlanningError(
            "No exact deterministic residential riser layout closes the floor height "
            "within the supported 150-190 mm planning range."
        )
    _delta, count, riser = min(candidates)
    return riser, count


def plan_vertical_architecture(
    *,
    seed_id: EntityId,
    buildable_area: BuildableArea,
    floor_buildable_areas: tuple[BuildableArea, ...],
    floor_count: int,
    floor_height_mm: int,
    solver_step_mm: int,
    search_variant: PlannerSearchVariant,
) -> VerticalCorePlan:
    """Reserve one deterministic core in the common footprint before floor solves."""

    if floor_count < 2:
        raise VerticalArchitecturePlanningError(
            "Building-level vertical-core planning requires a multi-floor request."
        )
    areas = floor_buildable_areas or tuple(buildable_area for _ in range(floor_count))
    if len(areas) != floor_count:
        raise VerticalArchitecturePlanningError(
            "Vertical-core planning requires one buildable footprint per served floor."
        )

    bounds = tuple(_polygon_bounds(area.polygon) for area in areas)
    common_min_x = _ceil_to_step(max(item[0] for item in bounds), solver_step_mm)
    common_min_y = _ceil_to_step(max(item[1] for item in bounds), solver_step_mm)
    common_max_x = _floor_to_step(min(item[2] for item in bounds), solver_step_mm)
    common_max_y = _floor_to_step(min(item[3] for item in bounds), solver_step_mm)
    width = _ceil_to_step(_CORE_WIDTH_MM, solver_step_mm)
    depth = _ceil_to_step(_CORE_DEPTH_MM, solver_step_mm)
    if common_max_x - common_min_x < width or common_max_y - common_min_y < depth:
        raise VerticalArchitecturePlanningError(
            "VERTICAL_CORE_UNPLACEABLE: common floor footprint cannot contain the "
            "supported 2300 x 3500 mm dog-legged stair core."
        )

    center_y = _floor_to_step(
        common_min_y + (common_max_y - common_min_y - depth) // 2,
        solver_step_mm,
    )
    positions = {
        PlannerSearchVariant.LOWER_LEFT: (common_min_x, common_min_y, 0),
        PlannerSearchVariant.LOWER_RIGHT: (common_max_x - width, common_min_y, 90_000_000),
        PlannerSearchVariant.UPPER_LEFT: (common_min_x, common_max_y - depth, 270_000_000),
        PlannerSearchVariant.UPPER_RIGHT: (
            common_max_x - width,
            common_max_y - depth,
            180_000_000,
        ),
        PlannerSearchVariant.REVERSE_LOWER_LEFT: (common_min_x, center_y, 0),
        PlannerSearchVariant.REVERSE_UPPER_RIGHT: (
            common_max_x - width,
            center_y,
            180_000_000,
        ),
    }
    x_mm, y_mm, direction_udeg = positions[search_variant]
    footprint = _rectangle(x_mm, y_mm, width, depth)
    riser_mm, riser_count = _stair_riser_geometry(floor_height_mm)
    identity = (
        f"{floor_count}|{x_mm}|{y_mm}|{width}|{depth}|{floor_height_mm}|"
        f"{search_variant.value}"
    )
    return VerticalCorePlan(
        core_id=uuid5(_CORE_NAMESPACE, f"{seed_id}|{identity}"),
        footprint=footprint,
        served_floor_indices=tuple(range(floor_count)),
        width_mm=_STAIR_WIDTH_MM,
        riser_mm=riser_mm,
        tread_mm=_STAIR_TREAD_MM,
        number_of_risers=riser_count,
        floor_height_mm=floor_height_mm,
        landing_depth_mm=_STAIR_LANDING_MM,
        direction_udeg=direction_udeg,
        headroom_mm=_STAIR_HEADROOM_MM,
        wet_stack_anchor=IntPoint(
            x_mm=x_mm + width // 2,
            y_mm=y_mm + depth // 2,
        ),
    )


def _room_center2(room: RoomGeometry) -> tuple[int, int]:
    min_x, min_y, max_x, max_y = _polygon_bounds(room.polygon)
    return min_x + max_x, min_y + max_y


def _center_distance_mm(first: RoomGeometry, second: RoomGeometry) -> int:
    first_center = _room_center2(first)
    second_center = _room_center2(second)
    return round(
        math.hypot(
            first_center[0] - second_center[0],
            first_center[1] - second_center[1],
        )
        / 2
    )


def _rectangles_overlap(first: IntPolygon, second: IntPolygon) -> bool:
    a = _polygon_bounds(first)
    b = _polygon_bounds(second)
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _rectangle_contains(container: IntPolygon, subject: IntPolygon) -> bool:
    outer = _polygon_bounds(container)
    inner = _polygon_bounds(subject)
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _wet_group(room_type: RoomType) -> str:
    return "SANITARY" if room_type in _SANITARY_ROOM_TYPES else "SERVICE"


def evaluate_wet_stacks(floors: tuple[Floor, ...]) -> WetStackEvaluation:
    pairs: list[WetStackPair] = []
    unpaired: list[EntityId] = []
    ordered = tuple(sorted(floors, key=lambda item: item.index))
    for lower, upper in pairwise(ordered):
        lower_wet = tuple(room for room in lower.rooms if room.room_type in _WET_ROOM_TYPES)
        upper_wet = tuple(room for room in upper.rooms if room.room_type in _WET_ROOM_TYPES)
        for upper_room in upper_wet:
            compatible = tuple(
                room
                for room in lower_wet
                if _wet_group(room.room_type) == _wet_group(upper_room.room_type)
            )
            if not compatible:
                unpaired.append(upper_room.id)
                continue
            lower_room = min(
                compatible,
                key=lambda room: (_center_distance_mm(room, upper_room), str(room.id)),
            )
            separation = _center_distance_mm(lower_room, upper_room)
            if _rectangles_overlap(lower_room.polygon, upper_room.polygon):
                relationship = WetStackRelationship.ALIGNED
            elif separation <= _WET_PROXIMITY_MM:
                relationship = WetStackRelationship.PROXIMATE
            else:
                relationship = WetStackRelationship.DISPERSED
            pairs.append(
                WetStackPair(
                    lower_floor_index=lower.index,
                    upper_floor_index=upper.index,
                    lower_room_id=lower_room.id,
                    upper_room_id=upper_room.id,
                    lower_room_type=lower_room.room_type,
                    upper_room_type=upper_room.room_type,
                    center_distance_mm=separation,
                    relationship=relationship,
                )
            )

    aligned = sum(item.relationship is WetStackRelationship.ALIGNED for item in pairs)
    proximate = sum(item.relationship is WetStackRelationship.PROXIMATE for item in pairs)
    dispersed = sum(item.relationship is WetStackRelationship.DISPERSED for item in pairs)
    denominator = len(pairs) + len(unpaired)
    score = 10_000
    if denominator:
        score = (aligned * 10_000 + proximate * 7_000 + dispersed * 2_500) // denominator
    return WetStackEvaluation(
        pairs=tuple(pairs),
        unpaired_upper_room_ids=tuple(sorted(unpaired, key=str)),
        aligned_count=aligned,
        proximate_count=proximate,
        dispersed_count=dispersed,
        score_basis_points=score,
    )


def _same_footprint(first: IntPolygon, second: IntPolygon, *, tolerance_mm: int = 0) -> bool:
    return all(
        abs(a - b) <= tolerance_mm
        for a, b in zip(_polygon_bounds(first), _polygon_bounds(second), strict=True)
    )


def validate_whole_building(
    *,
    floors: tuple[Floor, ...],
    expected_floor_count: int,
    expected_program: Counter[str],
    core_plan: VerticalCorePlan,
    internal_door_width_mm: int = 800,
    edge_margin_mm: int = 100,
    alignment_tolerance_mm: int = 50,
) -> WholeBuildingValidation:
    """Independently validate canonical whole-building access and vertical geometry."""

    diagnostics: list[BuildingDiagnostic] = []

    def add(
        code: str,
        severity: BuildingDiagnosticSeverity,
        message: str,
        *,
        floor_indices: tuple[int, ...] = (),
        entity_refs: tuple[EntityId, ...] = (),
    ) -> None:
        diagnostics.append(
            BuildingDiagnostic(
                code=code,
                severity=severity,
                message=message[:500],
                floor_indices=floor_indices,
                entity_refs=entity_refs[:16],
            )
        )

    ordered = tuple(sorted(floors, key=lambda item: item.index))
    if len(ordered) != expected_floor_count or tuple(item.index for item in ordered) != tuple(
        range(expected_floor_count)
    ):
        add(
            "INVALID_FLOOR_COUNT",
            BuildingDiagnosticSeverity.ERROR,
            "Canonical floors must be complete and consecutive from ground through "
            "the requested top floor.",
            floor_indices=tuple(item.index for item in ordered),
        )

    if core_plan.served_floor_indices != tuple(range(expected_floor_count)):
        add(
            "VERTICAL_CORE_FLOOR_RELATIONSHIP_INVALID",
            BuildingDiagnosticSeverity.ERROR,
            "The building-level core must explicitly serve every consecutive requested floor.",
            floor_indices=core_plan.served_floor_indices,
            entity_refs=(core_plan.core_id,),
        )

    actual_program = Counter(room.room_type.value for floor in ordered for room in floor.rooms)
    if actual_program != expected_program:
        add(
            "BUILDING_PROGRAM_INCOMPLETE",
            BuildingDiagnosticSeverity.ERROR,
            "Whole-building room program mismatch: "
            f"expected={dict(expected_program)} actual={dict(actual_program)}.",
        )

    stair_rooms_by_floor: dict[int, RoomGeometry] = {}
    floor_graphs = {}
    for floor in ordered:
        room_ids = {room.id for room in floor.rooms}
        wall_ids = {wall.id for wall in floor.walls}
        if len(room_ids) != len(floor.rooms) or len(wall_ids) != len(floor.walls) or any(
            opening.wall_id not in wall_ids for opening in floor.openings
        ):
            add(
                "CANONICAL_GEOMETRY_INCONSISTENT",
                BuildingDiagnosticSeverity.ERROR,
                "A floor contains duplicate room/wall identities or an opening with "
                "no canonical wall.",
                floor_indices=(floor.index,),
            )
        expected_elevation = (
            ordered[0].elevation_mm + floor.index * ordered[0].floor_to_floor_mm
            if ordered
            else 0
        )
        if floor.elevation_mm != expected_elevation or (
            ordered and floor.floor_to_floor_mm != ordered[0].floor_to_floor_mm
        ):
            add(
                "FLOOR_ELEVATION_INCONSISTENT",
                BuildingDiagnosticSeverity.ERROR,
                "Floor elevation does not close against its stable index and "
                "floor-to-floor height.",
                floor_indices=(floor.index,),
                entity_refs=(floor.id,),
            )

        stair_rooms = tuple(room for room in floor.rooms if room.room_type is RoomType.STAIRCASE)
        if len(stair_rooms) != 1 or len(floor.stairs) != 1:
            add(
                (
                    "VERTICAL_CORE_MISSING"
                    if not stair_rooms or not floor.stairs
                    else "VERTICAL_CORE_MULTIPLE"
                ),
                BuildingDiagnosticSeverity.ERROR,
                "Every served floor must contain exactly one staircase room and one "
                "canonical stair.",
                floor_indices=(floor.index,),
                entity_refs=tuple(room.id for room in stair_rooms),
            )
            continue
        stair_room = stair_rooms[0]
        stair = floor.stairs[0]
        stair_rooms_by_floor[floor.index] = stair_room
        if not _same_footprint(stair_room.polygon, stair.footprint) or not _same_footprint(
            stair.footprint,
            core_plan.footprint,
            tolerance_mm=alignment_tolerance_mm,
        ):
            add(
                "STAIR_CANONICAL_GEOMETRY_INVALID",
                BuildingDiagnosticSeverity.ERROR,
                "Canonical stair, staircase room and reserved core footprints must coincide.",
                floor_indices=(floor.index,),
                entity_refs=(stair_room.id, stair.id),
            )
        if (
            stair.width_mm != core_plan.width_mm
            or stair.riser_mm != core_plan.riser_mm
            or stair.tread_mm != core_plan.tread_mm
            or stair.number_of_risers != core_plan.number_of_risers
            or stair.floor_height_mm != core_plan.floor_height_mm
            or stair.landing_depth_mm != core_plan.landing_depth_mm
        ):
            add(
                "STAIR_DIMENSIONS_INCONSISTENT",
                BuildingDiagnosticSeverity.ERROR,
                "Canonical stair dimensions do not match the deterministic vertical-core plan.",
                floor_indices=(floor.index,),
                entity_refs=(stair.id,),
            )
        if (
            stair.stair_type is not core_plan.stair_type
            or stair.direction_udeg != core_plan.direction_udeg
            or stair.headroom_mm != core_plan.headroom_mm
            or stair.floor_height_mm != floor.floor_to_floor_mm
        ):
            add(
                "STAIR_DIMENSIONS_INCONSISTENT",
                BuildingDiagnosticSeverity.ERROR,
                "Canonical stair type, orientation, headroom and rise must match the "
                "core and floor relationship.",
                floor_indices=(floor.index,),
                entity_refs=(stair.id,),
            )
        if floor.boundary is None or not _rectangle_contains(floor.boundary, stair.footprint):
            add(
                "STAIR_OUTSIDE_FLOOR_FOOTPRINT",
                BuildingDiagnosticSeverity.ERROR,
                "Stair/core geometry must remain inside the canonical floor/buildable footprint.",
                floor_indices=(floor.index,),
                entity_refs=(stair.id,),
            )
        overlapping = tuple(
            room.id
            for room in floor.rooms
            if room.id != stair_room.id and _rectangles_overlap(stair.footprint, room.polygon)
        )
        if overlapping:
            add(
                "STAIR_ROOM_OVERLAP",
                BuildingDiagnosticSeverity.ERROR,
                "Stair footprint overlaps a non-stair required room.",
                floor_indices=(floor.index,),
                entity_refs=(stair.id, *overlapping),
            )

        anchor_ids = () if floor.index == 0 else (stair_room.id,)
        horizontal = validate_circulation(
            floor,
            internal_door_width_mm=internal_door_width_mm,
            edge_margin_mm=edge_margin_mm,
            require_external_entry=floor.index == 0,
            anchor_room_ids=anchor_ids,
        )
        floor_graphs[floor.index] = horizontal.graph
        if not horizontal.accepted:
            add(
                "HORIZONTAL_CIRCULATION_INVALID",
                BuildingDiagnosticSeverity.ERROR,
                f"Floor {floor.index}: {horizontal.message}",
                floor_indices=(floor.index,),
                entity_refs=horizontal.graph.disconnected_room_ids,
            )
        room_index = {room.id: room for room in floor.rooms}
        valid_access = any(
            stair_room.id in door.room_ids
            and any(
                room_id != stair_room.id
                and room_index[room_id].room_type in _CIRCULATION_CAPABLE_ROOM_TYPES
                for room_id in door.room_ids
            )
            for door in horizontal.graph.doors
        )
        if not valid_access:
            add(
                "STAIR_ACCESS_INVALID",
                BuildingDiagnosticSeverity.ERROR,
                "Stair must open directly to a circulation-capable non-sanitary space "
                "on every served floor.",
                floor_indices=(floor.index,),
                entity_refs=(stair_room.id,),
            )

    for lower_index in range(max(0, expected_floor_count - 1)):
        lower_room = stair_rooms_by_floor.get(lower_index)
        upper_room = stair_rooms_by_floor.get(lower_index + 1)
        if lower_room is None or upper_room is None:
            continue
        if not _same_footprint(
            lower_room.polygon,
            upper_room.polygon,
            tolerance_mm=alignment_tolerance_mm,
        ):
            add(
                "VERTICAL_CORE_MISALIGNED",
                BuildingDiagnosticSeverity.ERROR,
                "Consecutive staircase footprints are not vertically aligned.",
                floor_indices=(lower_index, lower_index + 1),
                entity_refs=(lower_room.id, upper_room.id),
            )

    node_rooms: dict[tuple[int, EntityId], RoomGeometry] = {}
    adjacency: dict[tuple[int, EntityId], set[tuple[int, EntityId]]] = defaultdict(set)
    entry_nodes: set[tuple[int, EntityId]] = set()
    transfers: list[VerticalTransfer] = []
    for floor in ordered:
        for room in floor.rooms:
            node_rooms[(floor.index, room.id)] = room
        graph = floor_graphs.get(floor.index)
        if graph is None:
            continue
        if floor.index == 0:
            entry_nodes.update((floor.index, room_id) for room_id in graph.entry_room_ids)
        for door in graph.doors:
            if len(door.room_ids) != 2:
                continue
            first = (floor.index, door.room_ids[0])
            second = (floor.index, door.room_ids[1])
            adjacency[first].add(second)
            adjacency[second].add(first)

    for lower_index in range(max(0, expected_floor_count - 1)):
        lower_room = stair_rooms_by_floor.get(lower_index)
        upper_room = stair_rooms_by_floor.get(lower_index + 1)
        if lower_room is None or upper_room is None:
            continue
        if not _same_footprint(
            lower_room.polygon,
            upper_room.polygon,
            tolerance_mm=alignment_tolerance_mm,
        ):
            continue
        lower_node = (lower_index, lower_room.id)
        upper_node = (lower_index + 1, upper_room.id)
        adjacency[lower_node].add(upper_node)
        adjacency[upper_node].add(lower_node)
        transfers.append(
            VerticalTransfer(
                lower_floor_index=lower_index,
                upper_floor_index=lower_index + 1,
                lower_room_id=lower_room.id,
                upper_room_id=upper_room.id,
            )
        )

    visited = set(entry_nodes)
    queue = deque(sorted(entry_nodes, key=lambda item: (item[0], str(item[1]))))
    while queue:
        current = queue.popleft()
        current_room = node_rooms.get(current)
        if current_room is not None and current_room.room_type in _SANITARY_ROOM_TYPES:
            continue
        for neighbour in sorted(adjacency[current], key=lambda item: (item[0], str(item[1]))):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    required = {
        node
        for node, room in node_rooms.items()
        if room.room_type not in _VEHICLE_ROOM_TYPES
    }
    disconnected = required - visited
    if disconnected:
        listed = ", ".join(
            f"floor={floor_index}:room={room_id}"
            for floor_index, room_id in sorted(
                disconnected,
                key=lambda item: (item[0], str(item[1])),
            )[:8]
        )
        add(
            "VERTICAL_CIRCULATION_DISCONNECTED",
            BuildingDiagnosticSeverity.ERROR,
            "Required rooms are unreachable from the main dwelling entry through "
            f"horizontal doors and aligned stairs: {listed}.",
            floor_indices=tuple(sorted({item[0] for item in disconnected})),
            entity_refs=tuple(
                item[1]
                for item in sorted(disconnected, key=lambda value: (value[0], str(value[1])))
            ),
        )

    wet_stack = evaluate_wet_stacks(ordered)
    if wet_stack.dispersed_count:
        add(
            "WET_STACK_DISPERSED",
            BuildingDiagnosticSeverity.WARNING,
            f"Detected {wet_stack.dispersed_count} materially dispersed consecutive-floor "
            "wet/service relationship(s); this remains a soft architectural preference.",
            entity_refs=tuple(
                pair.upper_room_id
                for pair in wet_stack.pairs
                if pair.relationship is WetStackRelationship.DISPERSED
            ),
        )
    if wet_stack.unpaired_upper_room_ids:
        add(
            "WET_STACK_UNPAIRED",
            BuildingDiagnosticSeverity.WARNING,
            "Upper-floor wet/service rooms have no compatible wet/service room on the "
            "immediately lower floor.",
            entity_refs=wet_stack.unpaired_upper_room_ids,
        )

    def nodes(values: set[tuple[int, EntityId]]) -> tuple[BuildingRoomNode, ...]:
        return tuple(
            BuildingRoomNode(floor_index=floor_index, room_id=room_id)
            for floor_index, room_id in sorted(values, key=lambda item: (item[0], str(item[1])))
        )

    diagnostics.sort(
        key=lambda item: (
            item.severity.value,
            item.code,
            item.floor_indices,
            tuple(str(ref) for ref in item.entity_refs),
        )
    )
    circulation = WholeBuildingCirculationGraph(
        entry_nodes=nodes(entry_nodes),
        required_nodes=nodes(required),
        reachable_nodes=nodes(visited),
        disconnected_nodes=nodes(disconnected),
        vertical_transfers=tuple(transfers),
    )
    accepted = not any(
        item.severity is BuildingDiagnosticSeverity.ERROR for item in diagnostics
    )
    return WholeBuildingValidation(
        accepted=accepted,
        diagnostics=tuple(diagnostics),
        circulation=circulation,
        wet_stack=wet_stack,
    )
