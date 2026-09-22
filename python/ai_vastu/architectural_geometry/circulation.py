from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import networkx as nx  # type: ignore[import-untyped]

from ai_vastu.plan_schema import (
    Floor,
    OpeningKind,
    RoomType,
    Wall,
    WallCategory,
)

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


@dataclass(frozen=True, slots=True)
class CirculationDoor:
    opening_id: UUID
    wall_id: UUID
    room_ids: tuple[UUID, ...]
    shared_wall_length_mm: int


@dataclass(frozen=True, slots=True)
class CirculationGraph:
    entry_room_ids: tuple[UUID, ...]
    doors: tuple[CirculationDoor, ...]
    reachable_room_ids: tuple[UUID, ...]
    required_room_ids: tuple[UUID, ...]
    disconnected_room_ids: tuple[UUID, ...]

    @property
    def connected(self) -> bool:
        return not self.disconnected_room_ids


@dataclass(frozen=True, slots=True)
class CirculationValidation:
    accepted: bool
    reason_code: str | None
    message: str
    graph: CirculationGraph


@dataclass(frozen=True, slots=True)
class CirculationTopologyAnalysis:
    root_room_ids: tuple[UUID, ...]
    reachable_room_ids: tuple[UUID, ...]
    disconnected_room_ids: tuple[UUID, ...]
    connected_components: tuple[tuple[UUID, ...], ...]
    articulation_room_ids: tuple[UUID, ...]


def analyze_room_access_graph(
    *,
    room_ids: tuple[UUID, ...],
    edges: tuple[tuple[UUID, UUID], ...],
    root_room_ids: tuple[UUID, ...],
    required_room_ids: tuple[UUID, ...],
    sanitary_room_ids: tuple[UUID, ...] = (),
) -> CirculationTopologyAnalysis:
    """Analyze circulation topology without asserting geometric validity.

    Callers remain responsible for proving that every supplied edge represents a
    physically door-capable relationship. Sanitary rooms may be reachable leaves,
    but are removed from the transit graph so they cannot bridge unrelated rooms.
    """

    known_room_ids = set(room_ids)
    referenced_room_ids = (
        set(root_room_ids)
        | set(required_room_ids)
        | set(sanitary_room_ids)
        | {room_id for edge in edges for room_id in edge}
    )
    unknown_room_ids = referenced_room_ids - known_room_ids
    if unknown_room_ids:
        listed = ", ".join(str(room_id) for room_id in sorted(unknown_room_ids, key=str))
        raise ValueError(f"Circulation graph references unknown room IDs: {listed}.")

    graph = nx.Graph()
    graph.add_nodes_from(room_ids)
    graph.add_edges_from(edges)

    sanitary = set(sanitary_room_ids)
    roots = tuple(sorted(set(root_room_ids), key=str))
    required = tuple(sorted(set(required_room_ids), key=str))

    transit_graph = graph.copy()
    transit_graph.remove_nodes_from(sanitary)

    reachable_non_sanitary: set[UUID] = set()
    for root in roots:
        if root in sanitary or root not in transit_graph:
            continue
        reachable_non_sanitary.update(nx.node_connected_component(transit_graph, root))

    reachable = set(reachable_non_sanitary) | (set(roots) & sanitary)
    for room_id in sorted(sanitary, key=str):
        if room_id not in graph:
            continue
        if any(neighbor in reachable_non_sanitary for neighbor in graph.neighbors(room_id)):
            reachable.add(room_id)

    disconnected = tuple(room_id for room_id in required if room_id not in reachable)
    components = tuple(
        tuple(sorted(component, key=str))
        for component in sorted(
            nx.connected_components(transit_graph),
            key=lambda component: tuple(str(item) for item in sorted(component, key=str)),
        )
    )
    articulation = tuple(sorted(nx.articulation_points(transit_graph), key=str))

    return CirculationTopologyAnalysis(
        root_room_ids=roots,
        reachable_room_ids=tuple(sorted(reachable, key=str)),
        disconnected_room_ids=disconnected,
        connected_components=components,
        articulation_room_ids=articulation,
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


def _wall_room_ids(wall: Wall, floor: Floor) -> tuple[UUID, ...]:
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
    for room in floor.rooms:
        points = room.polygon.outer
        for index, start in enumerate(points):
            end = points[(index + 1) % len(points)]
            edge = _edge_signature(start.x_mm, start.y_mm, end.x_mm, end.y_mm)
            if edge is None:
                continue
            edge_orientation, edge_fixed, edge_lo, edge_hi = edge
            if (
                edge_orientation == orientation
                and edge_fixed == fixed
                and _overlap_length((lo, hi), (edge_lo, edge_hi)) > 0
            ):
                adjacent.append(room.id)
                break
    return tuple(sorted(set(adjacent), key=str))


def _door_record(
    opening_id: UUID,
    wall: Wall,
    room_ids: tuple[UUID, ...],
) -> CirculationDoor:
    return CirculationDoor(
        opening_id=opening_id,
        wall_id=wall.id,
        room_ids=room_ids,
        shared_wall_length_mm=abs(wall.axis.end.x_mm - wall.axis.start.x_mm)
        + abs(wall.axis.end.y_mm - wall.axis.start.y_mm),
    )


def build_circulation_graph(
    floor: Floor,
    *,
    internal_door_width_mm: int = 800,
    edge_margin_mm: int = 100,
    require_external_entry: bool = True,
    anchor_room_ids: tuple[UUID, ...] = (),
) -> CirculationGraph:
    """Build the usable door graph from canonical walls and openings."""

    room_by_id = {room.id: room for room in floor.rooms}
    wall_by_id = {wall.id: wall for wall in floor.walls}
    doors: list[CirculationDoor] = []
    entries: list[UUID] = []
    invalid = False
    required_length = internal_door_width_mm + 2 * edge_margin_mm

    for opening in floor.openings:
        if opening.kind is not OpeningKind.DOOR:
            continue
        wall = wall_by_id.get(opening.wall_id)
        if wall is None:
            invalid = True
            continue
        room_ids = _wall_room_ids(wall, floor)
        if wall.category is WallCategory.EXTERNAL:
            if len(room_ids) == 1 and room_by_id[room_ids[0]].room_type not in _VEHICLE_ROOM_TYPES:
                entries.append(room_ids[0])
            else:
                invalid = True
            continue
        if len(room_ids) != 2:
            invalid = True
            continue
        shared_length = abs(wall.axis.end.x_mm - wall.axis.start.x_mm) + abs(
            wall.axis.end.y_mm - wall.axis.start.y_mm
        )
        if shared_length < required_length or opening.width_mm + 2 * edge_margin_mm > shared_length:
            invalid = True
            continue
        doors.append(_door_record(opening.id, wall, room_ids))

    required = tuple(
        sorted(
            (room.id for room in floor.rooms if room.room_type not in _VEHICLE_ROOM_TYPES),
            key=str,
        )
    )
    analysis = analyze_room_access_graph(
        room_ids=tuple(sorted(room_by_id, key=str)),
        edges=tuple(
            (door.room_ids[0], door.room_ids[1])
            for door in doors
            if len(door.room_ids) == 2
        ),
        root_room_ids=tuple(entries) + tuple(anchor_room_ids),
        required_room_ids=required,
        sanitary_room_ids=tuple(
            sorted(
                (
                    room_id
                    for room_id, room in room_by_id.items()
                    if room.room_type in _SANITARY_ROOM_TYPES
                ),
                key=str,
            )
        ),
    )
    reachable = set(analysis.reachable_room_ids)
    disconnected = analysis.disconnected_room_ids
    if invalid and not disconnected:
        disconnected = required
    return CirculationGraph(
        entry_room_ids=tuple(sorted(set(entries), key=str)),
        doors=tuple(sorted(doors, key=lambda item: str(item.opening_id))),
        reachable_room_ids=tuple(sorted(reachable, key=str)),
        required_room_ids=required,
        disconnected_room_ids=disconnected,
    )


def validate_circulation(
    floor: Floor,
    *,
    internal_door_width_mm: int = 800,
    edge_margin_mm: int = 100,
    require_external_entry: bool = True,
    anchor_room_ids: tuple[UUID, ...] = (),
) -> CirculationValidation:
    graph = build_circulation_graph(
        floor,
        internal_door_width_mm=internal_door_width_mm,
        edge_margin_mm=edge_margin_mm,
        require_external_entry=require_external_entry,
        anchor_room_ids=anchor_room_ids,
    )
    if require_external_entry and not graph.entry_room_ids:
        return CirculationValidation(
            accepted=False,
            reason_code="CIRCULATION_ENTRY_MISSING",
            message="No external dwelling entry door reaches a required interior room.",
            graph=graph,
        )
    if graph.disconnected_room_ids:
        ids = ", ".join(str(item) for item in graph.disconnected_room_ids)
        return CirculationValidation(
            accepted=False,
            reason_code="CIRCULATION_DISCONNECTED",
            message=f"Required rooms are not reachable from dwelling entry: {ids}.",
            graph=graph,
        )
    return CirculationValidation(
        accepted=True,
        reason_code=None,
        message="Every required interior room is reachable through valid door connections.",
        graph=graph,
    )