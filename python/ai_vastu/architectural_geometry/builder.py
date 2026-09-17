from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import pairwise
from uuid import UUID, uuid5

from ai_vastu.constraints.models import RoomInstance
from ai_vastu.plan_schema import (
    AxisSegment,
    Floor,
    IntPoint,
    IntPolygon,
    Opening,
    RoomGeometry,
    RoomType,
    Stair,
    Wall,
    WallCategory,
)
from ai_vastu.solver.models import PlannerStatus, RoomPlacement

from .errors import (
    ArchitecturalGeometryInputError,
    OpeningPlacementError,
    StairConstructionError,
)
from .models import (
    ArchitecturalGeometryRequest,
    ArchitecturalGeometryResult,
    GeometryNotice,
    GeometryNoticeSeverity,
    OpeningBuildRequest,
    StairBuildRequest,
)

_WALL_NAMESPACE = UUID("fd8f64f2-1f64-54e5-bb83-cffea250f7d4")
_OPENING_NAMESPACE = UUID("92a968d6-25ed-51d9-b19b-8f142324e817")
_STAIR_NAMESPACE = UUID("8205b783-183b-59f5-988f-bfef36b2b6d9")


@dataclass(frozen=True, order=True)
class _LineKey:
    orientation: str
    fixed: int


@dataclass(frozen=True, order=True)
class _Interval:
    lo: int
    hi: int


@dataclass(frozen=True, order=True)
class _AtomicSegment:
    orientation: str
    fixed: int
    lo: int
    hi: int

    def points(self) -> tuple[IntPoint, IntPoint]:
        if self.orientation == "H":
            return IntPoint(x_mm=self.lo, y_mm=self.fixed), IntPoint(x_mm=self.hi, y_mm=self.fixed)
        return IntPoint(x_mm=self.fixed, y_mm=self.lo), IntPoint(x_mm=self.fixed, y_mm=self.hi)

    @property
    def length_mm(self) -> int:
        return self.hi - self.lo


def _room_polygon(placement: RoomPlacement) -> IntPolygon:
    x0 = placement.x_mm
    y0 = placement.y_mm
    x1 = x0 + placement.width_mm
    y1 = y0 + placement.depth_mm
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x0, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y0),
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x0, y_mm=y1),
        )
    )


def _edge_interval(a: IntPoint, b: IntPoint) -> tuple[_LineKey, _Interval]:
    if a.y_mm == b.y_mm:
        return _LineKey("H", a.y_mm), _Interval(min(a.x_mm, b.x_mm), max(a.x_mm, b.x_mm))
    if a.x_mm == b.x_mm:
        return _LineKey("V", a.x_mm), _Interval(min(a.y_mm, b.y_mm), max(a.y_mm, b.y_mm))
    raise ArchitecturalGeometryInputError(
        "Phase 8 wall builder supports orthogonal room edges only."
    )


def _polygon_edges(polygon: IntPolygon) -> tuple[tuple[IntPoint, IntPoint], ...]:
    points = polygon.outer
    return tuple((points[i], points[(i + 1) % len(points)]) for i in range(len(points)))


def _atomic_room_segments(room_polygons: tuple[IntPolygon, ...]) -> tuple[_AtomicSegment, ...]:
    groups: dict[_LineKey, list[_Interval]] = defaultdict(list)
    for polygon in room_polygons:
        for a, b in _polygon_edges(polygon):
            key, interval = _edge_interval(a, b)
            groups[key].append(interval)

    atomic: list[_AtomicSegment] = []
    for key in sorted(groups):
        intervals = groups[key]
        cuts = sorted({value for interval in intervals for value in (interval.lo, interval.hi)})
        for lo, hi in pairwise(cuts):
            if lo == hi:
                continue
            if any(interval.lo <= lo and hi <= interval.hi for interval in intervals):
                atomic.append(_AtomicSegment(key.orientation, key.fixed, lo, hi))
    return tuple(sorted(set(atomic)))


def _segment_on_boundary(segment: _AtomicSegment, boundary: IntPolygon) -> bool:
    for a, b in _polygon_edges(boundary):
        try:
            key, interval = _edge_interval(a, b)
        except ArchitecturalGeometryInputError:
            continue
        if key.orientation != segment.orientation or key.fixed != segment.fixed:
            continue
        if interval.lo <= segment.lo and segment.hi <= interval.hi:
            return True
    return False


def _wall_id(floor_id: UUID, segment: _AtomicSegment) -> UUID:
    return uuid5(
        _WALL_NAMESPACE,
        f"{floor_id}|{segment.orientation}|{segment.fixed}|{segment.lo}|{segment.hi}",
    )


def _opening_id(request: OpeningBuildRequest) -> UUID:
    return uuid5(
        _OPENING_NAMESPACE,
        "|".join(
            (
                str(request.wall_id),
                request.kind.value,
                str(request.offset_from_wall_start_mm),
                str(request.width_mm),
                str(request.height_mm),
                str(request.sill_height_mm),
                str(request.hinge),
                str(request.swing),
            )
        ),
    )


def _stair_id(floor_id: UUID, request: StairBuildRequest) -> UUID:
    return uuid5(
        _STAIR_NAMESPACE,
        f"{floor_id}|{request.room_instance_id}|{request.stair_type.value}",
    )


def _wall_length(wall: Wall) -> int:
    return abs(wall.axis.end.x_mm - wall.axis.start.x_mm) + abs(
        wall.axis.end.y_mm - wall.axis.start.y_mm
    )


def _build_openings(
    requests: tuple[OpeningBuildRequest, ...],
    walls: tuple[Wall, ...],
) -> tuple[Opening, ...]:
    wall_index = {wall.id: wall for wall in walls}
    by_wall: dict[UUID, list[tuple[int, int]]] = defaultdict(list)
    result: list[Opening] = []
    for request in sorted(
        requests,
        key=lambda item: (
            str(item.wall_id),
            item.offset_from_wall_start_mm,
            item.width_mm,
            item.kind.value,
        ),
    ):
        wall = wall_index.get(request.wall_id)
        if wall is None:
            raise OpeningPlacementError(f"Opening references unknown wall {request.wall_id}.")
        start = request.offset_from_wall_start_mm
        end = start + request.width_mm
        if end > _wall_length(wall):
            raise OpeningPlacementError(
                f"Opening on wall {wall.id} extends beyond the wall axis length."
            )
        for prior_start, prior_end in by_wall[wall.id]:
            if start < prior_end and prior_start < end:
                raise OpeningPlacementError(f"Openings overlap on wall {wall.id}.")
        by_wall[wall.id].append((start, end))
        result.append(
            Opening(
                id=_opening_id(request),
                wall_id=wall.id,
                kind=request.kind,
                offset_from_wall_start_mm=request.offset_from_wall_start_mm,
                width_mm=request.width_mm,
                height_mm=request.height_mm,
                sill_height_mm=request.sill_height_mm,
                hinge=request.hinge,
                swing=request.swing,
            )
        )
    return tuple(result)


def _build_stairs(
    requests: tuple[StairBuildRequest, ...],
    placement_index: dict[UUID, RoomPlacement],
    room_polygon_index: dict[UUID, IntPolygon],
    floor_id: UUID,
) -> tuple[Stair, ...]:
    seen_rooms: set[UUID] = set()
    result: list[Stair] = []
    for request in sorted(requests, key=lambda item: str(item.room_instance_id)):
        placement = placement_index.get(request.room_instance_id)
        if placement is None:
            raise StairConstructionError(
                f"Stair references unknown room instance {request.room_instance_id}."
            )
        if placement.room_type is not RoomType.STAIRCASE:
            raise StairConstructionError("Stair requests must reference a staircase room instance.")
        if request.room_instance_id in seen_rooms:
            raise StairConstructionError("Only one Phase 8 stair may be built per staircase room.")
        seen_rooms.add(request.room_instance_id)
        if request.width_mm > min(placement.width_mm, placement.depth_mm):
            raise StairConstructionError(
                "Stair width exceeds its allocated staircase room envelope."
            )
        result.append(
            Stair(
                id=_stair_id(floor_id, request),
                stair_type=request.stair_type,
                footprint=room_polygon_index[request.room_instance_id],
                width_mm=request.width_mm,
                riser_mm=request.riser_mm,
                tread_mm=request.tread_mm,
                number_of_risers=request.number_of_risers,
                floor_height_mm=request.floor_height_mm,
                landing_depth_mm=request.landing_depth_mm,
                direction_udeg=request.direction_udeg,
                headroom_mm=request.headroom_mm,
            )
        )
    return tuple(result)


def build_architectural_geometry(
    request: ArchitecturalGeometryRequest,
) -> ArchitecturalGeometryResult:
    result = request.planner_result
    if result.status not in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
        raise ArchitecturalGeometryInputError(
            "Architectural geometry requires a feasible solver result."
        )

    problem_rooms: dict[UUID, RoomInstance] = {
        room.id: room for room in request.problem.room_instances
    }
    placements = tuple(sorted(result.placements, key=lambda item: str(item.room_instance_id)))
    placement_ids = {placement.room_instance_id for placement in placements}
    if placement_ids != set(problem_rooms):
        raise ArchitecturalGeometryInputError(
            "Solver placements must exactly match compiled problem room instances."
        )
    floor_indices = {placement.floor_index for placement in placements}
    if len(floor_indices) != 1:
        raise ArchitecturalGeometryInputError(
            "Phase 8 builder accepts one solver floor per request."
        )

    room_polygons = {
        placement.room_instance_id: _room_polygon(placement) for placement in placements
    }
    rooms = tuple(
        RoomGeometry(
            id=placement.room_instance_id,
            requirement_id=problem_rooms[placement.room_instance_id].requirement_id,
            room_type=placement.room_type,
            polygon=room_polygons[placement.room_instance_id],
            locked=problem_rooms[placement.room_instance_id].locked,
        )
        for placement in placements
    )

    wall_list: list[Wall] = []
    for segment in _atomic_room_segments(tuple(room_polygons.values())):
        external = _segment_on_boundary(segment, request.problem.buildable_area.polygon)
        category = WallCategory.EXTERNAL if external else WallCategory.INTERNAL
        thickness = (
            request.wall_config.external_wall_thickness_mm
            if external
            else request.wall_config.internal_wall_thickness_mm
        )
        construction_type = (
            request.wall_config.external_construction_type
            if external
            else request.wall_config.internal_construction_type
        )
        start, end = segment.points()
        wall_list.append(
            Wall(
                id=_wall_id(request.floor_id, segment),
                axis=AxisSegment(start=start, end=end),
                thickness_mm=thickness,
                height_mm=request.wall_config.wall_height_mm,
                category=category,
                construction_type=construction_type,
            )
        )
    walls = tuple(sorted(wall_list, key=lambda wall: str(wall.id)))
    openings = _build_openings(request.openings, walls)
    placement_index = {placement.room_instance_id: placement for placement in placements}
    stairs = _build_stairs(request.stairs, placement_index, room_polygons, request.floor_id)

    floor = Floor(
        id=request.floor_id,
        index=next(iter(floor_indices)),
        name=request.floor_name,
        elevation_mm=request.elevation_mm,
        floor_to_floor_mm=request.floor_to_floor_mm,
        boundary=request.problem.buildable_area.polygon,
        rooms=rooms,
        walls=walls,
        openings=openings,
        stairs=stairs,
    )
    notices = (
        GeometryNotice(
            code="ROOM_ENVELOPES_PRECEDE_WALL_CLEARANCE_VALIDATION",
            severity=GeometryNoticeSeverity.WARNING,
            message=(
                "Phase 7 room rectangles are preserved exactly as planning envelopes; "
                "wall thickness was not part of that solve. Phase 9 must independently "
                "validate architectural clearances."
            ),
        ),
    )
    built = ArchitecturalGeometryResult(
        source_problem_hash=request.problem.compute_content_hash(),
        source_planner_hash=result.compute_content_hash(),
        floor=floor,
        notices=notices,
    )
    return built.with_content_hash()
