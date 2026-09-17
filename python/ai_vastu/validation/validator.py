from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations
from uuid import UUID

from ai_vastu.constraints import (
    DimensionAxis,
    MinimumAreaConstraint,
    MinimumDimensionConstraint,
)
from ai_vastu.geometry import GeometryError, ShapelyGeometryValidator, VerifiedGeometryKernel
from ai_vastu.geometry.ring_math import area2_polygon
from ai_vastu.plan_schema import (
    DoorHinge,
    DoorSwing,
    EvidenceItem,
    IntPoint,
    IntPolygon,
    Opening,
    OpeningKind,
    RoomGeometry,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    Wall,
    WallCategory,
)

from .models import (
    VALIDATOR_VERSION,
    ArchitecturalValidationRequest,
    DoorSwingContext,
    SwingSpace,
    ValidationRunResult,
)

_LineKey = tuple[str, int]
_Interval = tuple[int, int]
_OUTSIDE = "__OUTSIDE__"


@dataclass(frozen=True, slots=True)
class _Edge:
    key: _LineKey
    lo: int
    hi: int


@dataclass(frozen=True, slots=True)
class _RoomBounds:
    min_x: int
    min_y: int
    max_x: int
    max_y: int

    @property
    def width_mm(self) -> int:
        return self.max_x - self.min_x

    @property
    def depth_mm(self) -> int:
        return self.max_y - self.min_y


def _result(
    check_id: str,
    severity: ValidationSeverity,
    message_code: str,
    *,
    entity_refs: Iterable[UUID] = (),
    evidence: dict[str, object] | None = None,
) -> ValidationResult:
    evidence_items = tuple(
        EvidenceItem(key=key, value=str(value)) for key, value in sorted((evidence or {}).items())
    )
    return ValidationResult(
        check_id=check_id,
        severity=severity,
        entity_refs=tuple(entity_refs),
        message_code=message_code,
        evidence=evidence_items,
        validator_version=VALIDATOR_VERSION,
    )


def _edge(a: IntPoint, b: IntPoint) -> _Edge | None:
    if a.y_mm == b.y_mm:
        return _Edge(("H", a.y_mm), min(a.x_mm, b.x_mm), max(a.x_mm, b.x_mm))
    if a.x_mm == b.x_mm:
        return _Edge(("V", a.x_mm), min(a.y_mm, b.y_mm), max(a.y_mm, b.y_mm))
    return None


def _polygon_edges(polygon: IntPolygon) -> tuple[_Edge, ...] | None:
    edges: list[_Edge] = []
    for index, a in enumerate(polygon.outer):
        b = polygon.outer[(index + 1) % len(polygon.outer)]
        current = _edge(a, b)
        if current is None:
            return None
        edges.append(current)
    return tuple(edges)


def _wall_edge(wall: Wall) -> _Edge | None:
    return _edge(wall.axis.start, wall.axis.end)


def _overlap_length(first: _Interval, second: _Interval) -> int:
    return max(0, min(first[1], second[1]) - max(first[0], second[0]))


def _interval_covered(target: _Interval, intervals: Iterable[_Interval]) -> bool:
    lo, hi = target
    clipped = sorted(
        (max(lo, start), min(hi, end))
        for start, end in intervals
        if _overlap_length(target, (start, end)) > 0
    )
    cursor = lo
    for start, end in clipped:
        if start > cursor:
            return False
        cursor = max(cursor, end)
        if cursor >= hi:
            return True
    return cursor >= hi


def _rectangle_bounds(room: RoomGeometry) -> _RoomBounds | None:
    polygon = room.polygon
    if polygon.holes or len(polygon.outer) != 4:
        return None
    xs = {point.x_mm for point in polygon.outer}
    ys = {point.y_mm for point in polygon.outer}
    if len(xs) != 2 or len(ys) != 2:
        return None
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    expected = {
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    }
    actual = {(point.x_mm, point.y_mm) for point in polygon.outer}
    if actual != expected:
        return None
    return _RoomBounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def _wall_length_mm(wall: Wall) -> int:
    return abs(wall.axis.end.x_mm - wall.axis.start.x_mm) + abs(
        wall.axis.end.y_mm - wall.axis.start.y_mm
    )


def _wall_adjacency(
    wall: Wall,
    rooms: tuple[RoomGeometry, ...],
) -> tuple[UUID, ...]:
    wall_edge = _wall_edge(wall)
    if wall_edge is None:
        return ()
    adjacent: list[UUID] = []
    for room in rooms:
        room_edges = _polygon_edges(room.polygon)
        if room_edges is None:
            continue
        if any(
            edge.key == wall_edge.key
            and _overlap_length((edge.lo, edge.hi), (wall_edge.lo, wall_edge.hi)) > 0
            for edge in room_edges
        ):
            adjacent.append(room.id)
    return tuple(sorted(adjacent, key=str))


def _opening_point(wall: Wall, offset_mm: int) -> IntPoint:
    dx = wall.axis.end.x_mm - wall.axis.start.x_mm
    dy = wall.axis.end.y_mm - wall.axis.start.y_mm
    length = _wall_length_mm(wall)
    step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
    step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
    if offset_mm > length:
        raise ValueError("Opening offset exceeds wall length.")
    return IntPoint(
        x_mm=wall.axis.start.x_mm + step_x * offset_mm,
        y_mm=wall.axis.start.y_mm + step_y * offset_mm,
    )


def _swing_envelope(
    wall: Wall,
    opening: Opening,
    *,
    target_room: RoomGeometry | None,
    exterior_room: RoomGeometry | None,
    margin_mm: int,
) -> IntPolygon | None:
    if opening.hinge is None:
        return None
    start = _opening_point(wall, opening.offset_from_wall_start_mm)
    end = _opening_point(wall, opening.offset_from_wall_start_mm + opening.width_mm)
    hinge = start if opening.hinge is DoorHinge.LEFT else end
    other = end if opening.hinge is DoorHinge.LEFT else start
    tangent_x = 0 if other.x_mm == hinge.x_mm else (1 if other.x_mm > hinge.x_mm else -1)
    tangent_y = 0 if other.y_mm == hinge.y_mm else (1 if other.y_mm > hinge.y_mm else -1)

    reference = target_room or exterior_room
    if reference is None:
        return None
    bounds = _rectangle_bounds(reference)
    if bounds is None:
        return None
    center_x2 = bounds.min_x + bounds.max_x
    center_y2 = bounds.min_y + bounds.max_y
    wall_x2 = wall.axis.start.x_mm + wall.axis.end.x_mm
    wall_y2 = wall.axis.start.y_mm + wall.axis.end.y_mm

    if wall.axis.start.y_mm == wall.axis.end.y_mm:
        room_normal_y = 1 if center_y2 > wall_y2 else -1
        normal_x = 0
        normal_y = room_normal_y
    elif wall.axis.start.x_mm == wall.axis.end.x_mm:
        room_normal_x = 1 if center_x2 > wall_x2 else -1
        normal_x = room_normal_x
        normal_y = 0
    else:
        return None

    if target_room is None:
        normal_x *= -1
        normal_y *= -1

    sweep = opening.width_mm + margin_mm
    p0 = hinge
    p1 = IntPoint(
        x_mm=hinge.x_mm + tangent_x * sweep,
        y_mm=hinge.y_mm + tangent_y * sweep,
    )
    p2 = IntPoint(
        x_mm=p1.x_mm + normal_x * sweep,
        y_mm=p1.y_mm + normal_y * sweep,
    )
    p3 = IntPoint(
        x_mm=hinge.x_mm + normal_x * sweep,
        y_mm=hinge.y_mm + normal_y * sweep,
    )
    return IntPolygon(outer=(p0, p1, p2, p3))


def _validate_polygon_topology(
    name: str,
    polygon: IntPolygon,
    *,
    entity_refs: tuple[UUID, ...],
    validator: ShapelyGeometryValidator,
    errors: list[ValidationResult],
) -> bool:
    try:
        validator.validate_polygon(polygon)
    except GeometryError as exc:
        errors.append(
            _result(
                f"phase9.{name}.topology",
                ValidationSeverity.ERROR,
                "INVALID_POLYGON_TOPOLOGY",
                entity_refs=entity_refs,
                evidence={"reason": str(exc)},
            )
        )
        return False
    return True


def _validate_source_integrity(
    request: ArchitecturalValidationRequest,
    errors: list[ValidationResult],
) -> None:
    expected_problem_hash = request.problem.compute_content_hash()
    if request.geometry.source_problem_hash != expected_problem_hash:
        errors.append(
            _result(
                "phase9.provenance.problem_hash",
                ValidationSeverity.ERROR,
                "SOURCE_PROBLEM_HASH_MISMATCH",
                evidence={
                    "expected": expected_problem_hash,
                    "actual": request.geometry.source_problem_hash,
                },
            )
        )


def _validate_containment_and_overlap(
    request: ArchitecturalValidationRequest,
    kernel: VerifiedGeometryKernel,
    errors: list[ValidationResult],
) -> None:
    floor = request.geometry.floor
    if floor.boundary is None:
        errors.append(
            _result(
                "phase9.floor.boundary",
                ValidationSeverity.ERROR,
                "FLOOR_BOUNDARY_MISSING",
                entity_refs=(floor.id,),
            )
        )
        return

    try:
        if not kernel.contains(request.plot_boundary, request.problem.buildable_area.polygon):
            errors.append(
                _result(
                    "phase9.buildable.plot_containment",
                    ValidationSeverity.ERROR,
                    "BUILDABLE_AREA_OUTSIDE_PLOT",
                )
            )
        mismatch = kernel.xor((floor.boundary,), (request.problem.buildable_area.polygon,))
        if not mismatch.is_empty:
            errors.append(
                _result(
                    "phase9.floor.buildable_parity",
                    ValidationSeverity.ERROR,
                    "FLOOR_BOUNDARY_DIFFERS_FROM_BUILDABLE_AREA",
                    entity_refs=(floor.id,),
                )
            )
        for room in floor.rooms:
            if not kernel.contains(floor.boundary, room.polygon):
                errors.append(
                    _result(
                        "phase9.room.containment",
                        ValidationSeverity.ERROR,
                        "ROOM_OUTSIDE_FLOOR_BOUNDARY",
                        entity_refs=(room.id,),
                    )
                )
        for first, second in combinations(floor.rooms, 2):
            intersection = kernel.intersection((first.polygon,), (second.polygon,))
            if sum(area2_polygon(polygon) for polygon in intersection.polygons) > 0:
                errors.append(
                    _result(
                        "phase9.room.overlap",
                        ValidationSeverity.ERROR,
                        "ROOM_INTERIOR_OVERLAP",
                        entity_refs=(first.id, second.id),
                    )
                )
    except GeometryError as exc:
        errors.append(
            _result(
                "phase9.geometry.kernel",
                ValidationSeverity.ERROR,
                "GEOMETRY_KERNEL_VERIFICATION_FAILED",
                evidence={"reason": str(exc)},
            )
        )


def _validate_slivers(
    request: ArchitecturalValidationRequest,
    errors: list[ValidationResult],
) -> None:
    threshold_area2 = request.config.tiny_sliver_area_mm2 * 2
    for room in request.geometry.floor.rooms:
        area2 = area2_polygon(room.polygon)
        if area2 < threshold_area2:
            errors.append(
                _result(
                    "phase9.room.sliver",
                    ValidationSeverity.ERROR,
                    "TINY_SLIVER_ROOM_POLYGON",
                    entity_refs=(room.id,),
                    evidence={
                        "area2_mm2": area2,
                        "threshold_area2_mm2": threshold_area2,
                    },
                )
            )


def _validate_duplicate_entities(
    request: ArchitecturalValidationRequest,
    errors: list[ValidationResult],
) -> None:
    floor = request.geometry.floor
    entities: list[tuple[str, UUID]] = []
    for kind, values in (
        ("room", floor.rooms),
        ("wall", floor.walls),
        ("opening", floor.openings),
        ("stair", floor.stairs),
    ):
        entities.extend((kind, value.id) for value in values)
    seen: dict[UUID, str] = {}
    for kind, entity_id in entities:
        prior = seen.get(entity_id)
        if prior is not None:
            errors.append(
                _result(
                    "phase9.entity.duplicate_id",
                    ValidationSeverity.ERROR,
                    "DUPLICATE_ENTITY_ID",
                    entity_refs=(entity_id,),
                    evidence={"first_kind": prior, "duplicate_kind": kind},
                )
            )
        else:
            seen[entity_id] = kind

    wall_geometry: dict[tuple[_LineKey, int, int], UUID] = {}
    for wall in floor.walls:
        current = _wall_edge(wall)
        if current is None:
            continue
        signature = (current.key, current.lo, current.hi)
        prior_id = wall_geometry.get(signature)
        if prior_id is not None:
            errors.append(
                _result(
                    "phase9.wall.duplicate_geometry",
                    ValidationSeverity.ERROR,
                    "DUPLICATE_WALL_GEOMETRY",
                    entity_refs=(prior_id, wall.id),
                )
            )
        else:
            wall_geometry[signature] = wall.id


def _validate_walls_and_dimension_closure(
    request: ArchitecturalValidationRequest,
    errors: list[ValidationResult],
    topology_validator: ShapelyGeometryValidator,
) -> dict[UUID, tuple[UUID, ...]]:
    floor = request.geometry.floor
    adjacency: dict[UUID, tuple[UUID, ...]] = {}
    wall_by_key: dict[_LineKey, list[tuple[_Interval, Wall]]] = defaultdict(list)

    for wall in floor.walls:
        current = _wall_edge(wall)
        if current is None:
            errors.append(
                _result(
                    "phase9.wall.orthogonal",
                    ValidationSeverity.ERROR,
                    "NON_ORTHOGONAL_WALL_AXIS",
                    entity_refs=(wall.id,),
                )
            )
            continue
        wall_by_key[current.key].append(((current.lo, current.hi), wall))
        adjacent = _wall_adjacency(wall, floor.rooms)
        adjacency[wall.id] = adjacent
        if not adjacent:
            errors.append(
                _result(
                    "phase9.wall.orphan",
                    ValidationSeverity.ERROR,
                    "ORPHAN_WALL",
                    entity_refs=(wall.id,),
                )
            )
        if floor.boundary is not None and not topology_validator.covers_axis_segment(
            floor.boundary, wall.axis
        ):
            errors.append(
                _result(
                    "phase9.wall.floor_containment",
                    ValidationSeverity.ERROR,
                    "WALL_OUTSIDE_FLOOR_BOUNDARY",
                    entity_refs=(wall.id,),
                )
            )

    for room in floor.rooms:
        edges = _polygon_edges(room.polygon)
        if edges is None:
            errors.append(
                _result(
                    "phase9.room.wall_closure",
                    ValidationSeverity.ERROR,
                    "ROOM_WALL_CLOSURE_REQUIRES_ORTHOGONAL_EDGES",
                    entity_refs=(room.id,),
                )
            )
            continue
        for edge in edges:
            intervals = [interval for interval, _wall in wall_by_key.get(edge.key, [])]
            if not _interval_covered((edge.lo, edge.hi), intervals):
                errors.append(
                    _result(
                        "phase9.room.wall_closure",
                        ValidationSeverity.ERROR,
                        "ROOM_BOUNDARY_NOT_FULLY_COVERED_BY_WALL_AXES",
                        entity_refs=(room.id,),
                        evidence={
                            "orientation": edge.key[0],
                            "fixed_mm": edge.key[1],
                            "start_mm": edge.lo,
                            "end_mm": edge.hi,
                        },
                    )
                )
    return adjacency


def _side_thickness(
    key: _LineKey,
    target: _Interval,
    walls: tuple[Wall, ...],
) -> int | None:
    thicknesses: list[int] = []
    intervals: list[_Interval] = []
    for wall in walls:
        edge = _wall_edge(wall)
        if edge is None or edge.key != key:
            continue
        overlap = _overlap_length(target, (edge.lo, edge.hi))
        if overlap <= 0:
            continue
        intervals.append((edge.lo, edge.hi))
        thicknesses.append(wall.thickness_mm)
    if not _interval_covered(target, intervals) or not thicknesses:
        return None
    return max(thicknesses)


def _validate_clear_dimensions(
    request: ArchitecturalValidationRequest,
    errors: list[ValidationResult],
) -> None:
    floor = request.geometry.floor
    min_dimensions: dict[UUID, dict[DimensionAxis, int]] = defaultdict(dict)
    min_areas: dict[UUID, int] = {}
    for constraint in request.problem.hard_constraints:
        if isinstance(constraint, MinimumDimensionConstraint):
            min_dimensions[constraint.room_instance_id][constraint.axis] = constraint.minimum_mm
        elif isinstance(constraint, MinimumAreaConstraint):
            min_areas[constraint.room_instance_id] = constraint.minimum_area_mm2

    for room in floor.rooms:
        bounds = _rectangle_bounds(room)
        if bounds is None:
            errors.append(
                _result(
                    "phase9.room.clear_dimensions",
                    ValidationSeverity.ERROR,
                    "CLEAR_DIMENSION_VALIDATION_REQUIRES_RECTANGULAR_ROOM",
                    entity_refs=(room.id,),
                )
            )
            continue

        left = _side_thickness(
            ("V", bounds.min_x),
            (bounds.min_y, bounds.max_y),
            floor.walls,
        )
        right = _side_thickness(
            ("V", bounds.max_x),
            (bounds.min_y, bounds.max_y),
            floor.walls,
        )
        bottom = _side_thickness(
            ("H", bounds.min_y),
            (bounds.min_x, bounds.max_x),
            floor.walls,
        )
        top = _side_thickness(
            ("H", bounds.max_y),
            (bounds.min_x, bounds.max_x),
            floor.walls,
        )
        if None in (left, right, bottom, top):
            errors.append(
                _result(
                    "phase9.room.clear_dimensions",
                    ValidationSeverity.ERROR,
                    "CLEAR_DIMENSION_WALL_COVERAGE_INCOMPLETE",
                    entity_refs=(room.id,),
                )
            )
            continue
        assert left is not None
        assert right is not None
        assert bottom is not None
        assert top is not None
        clear_width_2mm = 2 * bounds.width_mm - left - right
        clear_depth_2mm = 2 * bounds.depth_mm - bottom - top

        minimums = min_dimensions.get(room.id, {})
        min_width = minimums.get(DimensionAxis.WIDTH)
        if min_width is not None and clear_width_2mm < 2 * min_width:
            errors.append(
                _result(
                    "phase9.room.minimum_clear_width",
                    ValidationSeverity.ERROR,
                    "ROOM_CLEAR_WIDTH_BELOW_MINIMUM",
                    entity_refs=(room.id,),
                    evidence={
                        "clear_width_2mm": clear_width_2mm,
                        "minimum_width_2mm": 2 * min_width,
                    },
                )
            )
        min_depth = minimums.get(DimensionAxis.DEPTH)
        if min_depth is not None and clear_depth_2mm < 2 * min_depth:
            errors.append(
                _result(
                    "phase9.room.minimum_clear_depth",
                    ValidationSeverity.ERROR,
                    "ROOM_CLEAR_DEPTH_BELOW_MINIMUM",
                    entity_refs=(room.id,),
                    evidence={
                        "clear_depth_2mm": clear_depth_2mm,
                        "minimum_depth_2mm": 2 * min_depth,
                    },
                )
            )
        min_area = min_areas.get(room.id)
        if min_area is not None:
            clear_area_4mm2 = clear_width_2mm * clear_depth_2mm
            if clear_area_4mm2 < 4 * min_area:
                errors.append(
                    _result(
                        "phase9.room.minimum_clear_area",
                        ValidationSeverity.ERROR,
                        "ROOM_CLEAR_AREA_BELOW_MINIMUM",
                        entity_refs=(room.id,),
                        evidence={
                            "clear_area_4mm2": clear_area_4mm2,
                            "minimum_area_4mm2": 4 * min_area,
                        },
                    )
                )


def _validate_openings(
    request: ArchitecturalValidationRequest,
    adjacency: dict[UUID, tuple[UUID, ...]],
    kernel: VerifiedGeometryKernel,
    errors: list[ValidationResult],
    warnings: list[ValidationResult],
) -> None:
    floor = request.geometry.floor
    wall_index = {wall.id: wall for wall in floor.walls}
    room_index = {room.id: room for room in floor.rooms}
    context_index: dict[UUID, DoorSwingContext] = {}
    for context in request.swing_contexts:
        if context.opening_id in context_index:
            errors.append(
                _result(
                    "phase9.door.swing_context",
                    ValidationSeverity.ERROR,
                    "DUPLICATE_SWING_CONTEXT",
                    entity_refs=(context.opening_id,),
                )
            )
        else:
            context_index[context.opening_id] = context

    by_wall: dict[UUID, list[tuple[int, int, UUID]]] = defaultdict(list)
    opening_ids = {opening.id for opening in floor.openings}
    for context in request.swing_contexts:
        if context.opening_id not in opening_ids:
            errors.append(
                _result(
                    "phase9.door.swing_context",
                    ValidationSeverity.ERROR,
                    "SWING_CONTEXT_REFERENCES_UNKNOWN_OPENING",
                    entity_refs=(context.opening_id,),
                )
            )

    for opening in floor.openings:
        wall = wall_index.get(opening.wall_id)
        if wall is None:
            errors.append(
                _result(
                    "phase9.opening.wall_reference",
                    ValidationSeverity.ERROR,
                    "OPENING_REFERENCES_UNKNOWN_WALL",
                    entity_refs=(opening.id, opening.wall_id),
                )
            )
            continue
        start = opening.offset_from_wall_start_mm
        end = start + opening.width_mm
        if end > _wall_length_mm(wall):
            errors.append(
                _result(
                    "phase9.opening.wall_bounds",
                    ValidationSeverity.ERROR,
                    "OPENING_EXTENDS_BEYOND_WALL",
                    entity_refs=(opening.id, wall.id),
                )
            )
        for prior_start, prior_end, prior_id in by_wall[wall.id]:
            if start < prior_end and prior_start < end:
                errors.append(
                    _result(
                        "phase9.opening.overlap",
                        ValidationSeverity.ERROR,
                        "OPENINGS_OVERLAP_ON_WALL",
                        entity_refs=(prior_id, opening.id, wall.id),
                    )
                )
        by_wall[wall.id].append((start, end, opening.id))

        if opening.kind is not OpeningKind.DOOR:
            continue
        if opening.swing in (None, DoorSwing.NONE, DoorSwing.SLIDING):
            if opening.id in context_index:
                warnings.append(
                    _result(
                        "phase9.door.swing_context",
                        ValidationSeverity.WARNING,
                        "SWING_CONTEXT_UNUSED_FOR_NON_SWINGING_DOOR",
                        entity_refs=(opening.id,),
                    )
                )
            continue
        if opening.hinge is None:
            errors.append(
                _result(
                    "phase9.door.hinge",
                    ValidationSeverity.ERROR,
                    "SWINGING_DOOR_REQUIRES_HINGE",
                    entity_refs=(opening.id,),
                )
            )
            continue
        swing_context = context_index.get(opening.id)
        if swing_context is None:
            errors.append(
                _result(
                    "phase9.door.swing_context",
                    ValidationSeverity.ERROR,
                    "SWINGING_DOOR_REQUIRES_EXPLICIT_CLEARANCE_CONTEXT",
                    entity_refs=(opening.id,),
                )
            )
            continue

        adjacent_room_ids = adjacency.get(wall.id, ())
        target_room: RoomGeometry | None = None
        exterior_room: RoomGeometry | None = None
        if swing_context.swing_space is SwingSpace.ROOM:
            if swing_context.room_id not in adjacent_room_ids:
                errors.append(
                    _result(
                        "phase9.door.swing_context",
                        ValidationSeverity.ERROR,
                        "SWING_ROOM_IS_NOT_ADJACENT_TO_DOOR_WALL",
                        entity_refs=(opening.id,),
                        evidence={"room_id": swing_context.room_id},
                    )
                )
                continue
            assert swing_context.room_id is not None
            target_room = room_index[swing_context.room_id]
        else:
            if wall.category is not WallCategory.EXTERNAL or len(adjacent_room_ids) != 1:
                errors.append(
                    _result(
                        "phase9.door.swing_context",
                        ValidationSeverity.ERROR,
                        "EXTERIOR_SWING_REQUIRES_SINGLE_ROOM_EXTERNAL_WALL",
                        entity_refs=(opening.id, wall.id),
                    )
                )
                continue
            exterior_room = room_index[adjacent_room_ids[0]]

        envelope = _swing_envelope(
            wall,
            opening,
            target_room=target_room,
            exterior_room=exterior_room,
            margin_mm=request.config.door_clearance_margin_mm,
        )
        if envelope is None:
            errors.append(
                _result(
                    "phase9.door.swing_clearance",
                    ValidationSeverity.ERROR,
                    "DOOR_SWING_CLEARANCE_ENVELOPE_UNRESOLVED",
                    entity_refs=(opening.id,),
                )
            )
            continue
        try:
            if target_room is not None:
                clear = kernel.contains(target_room.polygon, envelope)
            else:
                clear = kernel.contains(request.plot_boundary, envelope)
                if clear:
                    for room in floor.rooms:
                        intersection = kernel.intersection((room.polygon,), (envelope,))
                        if sum(area2_polygon(poly) for poly in intersection.polygons) > 0:
                            clear = False
                            break
            if not clear:
                errors.append(
                    _result(
                        "phase9.door.swing_clearance",
                        ValidationSeverity.ERROR,
                        "DOOR_SWING_CLEARANCE_BLOCKED",
                        entity_refs=(opening.id,),
                    )
                )
        except GeometryError as exc:
            errors.append(
                _result(
                    "phase9.door.swing_clearance",
                    ValidationSeverity.ERROR,
                    "DOOR_SWING_GEOMETRY_VERIFICATION_FAILED",
                    entity_refs=(opening.id,),
                    evidence={"reason": str(exc)},
                )
            )


def _validate_circulation(
    request: ArchitecturalValidationRequest,
    adjacency: dict[UUID, tuple[UUID, ...]],
    errors: list[ValidationResult],
) -> None:
    floor = request.geometry.floor
    wall_index = {wall.id: wall for wall in floor.walls}
    graph: dict[str, set[str]] = defaultdict(set)
    for room in floor.rooms:
        graph[str(room.id)]
    graph[_OUTSIDE]

    for opening in floor.openings:
        if opening.kind not in (OpeningKind.DOOR, OpeningKind.OPENING):
            continue
        wall = wall_index.get(opening.wall_id)
        if wall is None:
            continue
        adjacent = adjacency.get(wall.id, ())
        if wall.category is WallCategory.EXTERNAL:
            for room_id in adjacent:
                graph[_OUTSIDE].add(str(room_id))
                graph[str(room_id)].add(_OUTSIDE)
        for first, second in combinations(adjacent, 2):
            graph[str(first)].add(str(second))
            graph[str(second)].add(str(first))

    visited = {_OUTSIDE}
    queue = deque([_OUTSIDE])
    while queue:
        current = queue.popleft()
        for neighbour in sorted(graph[current]):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append(neighbour)

    for room in floor.rooms:
        if str(room.id) not in visited:
            errors.append(
                _result(
                    "phase9.circulation.reachability",
                    ValidationSeverity.ERROR,
                    "UNREACHABLE_ROOM_FROM_EXTERIOR_ACCESS",
                    entity_refs=(room.id,),
                )
            )


def _validate_stairs(
    request: ArchitecturalValidationRequest,
    kernel: VerifiedGeometryKernel,
    errors: list[ValidationResult],
    warnings: list[ValidationResult],
) -> None:
    floor = request.geometry.floor
    stair_rooms = {room.id: room for room in floor.rooms if room.room_type.value == "staircase"}
    for stair in floor.stairs:
        matching: RoomGeometry | None = None
        for room in stair_rooms.values():
            try:
                mismatch = kernel.xor((stair.footprint,), (room.polygon,))
            except GeometryError as exc:
                errors.append(
                    _result(
                        "phase9.stair.geometry",
                        ValidationSeverity.ERROR,
                        "STAIR_GEOMETRY_VERIFICATION_FAILED",
                        entity_refs=(stair.id,),
                        evidence={"reason": str(exc)},
                    )
                )
                break
            if mismatch.is_empty:
                matching = room
                break
        if matching is None:
            errors.append(
                _result(
                    "phase9.stair.room_footprint",
                    ValidationSeverity.ERROR,
                    "STAIR_FOOTPRINT_DOES_NOT_MATCH_STAIRCASE_ROOM",
                    entity_refs=(stair.id,),
                )
            )
        if stair.riser_mm * stair.number_of_risers != stair.floor_height_mm:
            errors.append(
                _result(
                    "phase9.stair.vertical_closure",
                    ValidationSeverity.ERROR,
                    "STAIR_RISERS_DO_NOT_CLOSE_FLOOR_HEIGHT",
                    entity_refs=(stair.id,),
                    evidence={
                        "riser_times_count_mm": stair.riser_mm * stair.number_of_risers,
                        "floor_height_mm": stair.floor_height_mm,
                    },
                )
            )
        if stair.headroom_mm is None:
            warnings.append(
                _result(
                    "phase9.stair.headroom",
                    ValidationSeverity.WARNING,
                    "STAIR_HEADROOM_NOT_PROVIDED",
                    entity_refs=(stair.id,),
                )
            )


def _sort_results(values: list[ValidationResult]) -> tuple[ValidationResult, ...]:
    return tuple(
        sorted(
            values,
            key=lambda item: (
                item.check_id,
                item.message_code,
                tuple(str(ref) for ref in item.entity_refs),
                tuple((e.key, e.value) for e in item.evidence),
            ),
        )
    )


def validate_architectural_geometry(
    request: ArchitecturalValidationRequest,
) -> ValidationRunResult:
    errors: list[ValidationResult] = []
    warnings: list[ValidationResult] = []
    informational: list[ValidationResult] = []
    topology_validator = ShapelyGeometryValidator()
    kernel = VerifiedGeometryKernel()

    _validate_source_integrity(request, errors)
    _validate_polygon_topology(
        "plot",
        request.plot_boundary,
        entity_refs=(),
        validator=topology_validator,
        errors=errors,
    )
    _validate_polygon_topology(
        "buildable",
        request.problem.buildable_area.polygon,
        entity_refs=(),
        validator=topology_validator,
        errors=errors,
    )
    floor = request.geometry.floor
    if floor.boundary is not None:
        _validate_polygon_topology(
            "floor",
            floor.boundary,
            entity_refs=(floor.id,),
            validator=topology_validator,
            errors=errors,
        )
    for room in floor.rooms:
        _validate_polygon_topology(
            "room",
            room.polygon,
            entity_refs=(room.id,),
            validator=topology_validator,
            errors=errors,
        )
    for stair in floor.stairs:
        _validate_polygon_topology(
            "stair",
            stair.footprint,
            entity_refs=(stair.id,),
            validator=topology_validator,
            errors=errors,
        )

    _validate_duplicate_entities(request, errors)
    _validate_containment_and_overlap(request, kernel, errors)
    _validate_slivers(request, errors)
    adjacency = _validate_walls_and_dimension_closure(request, errors, topology_validator)
    _validate_clear_dimensions(request, errors)
    _validate_openings(request, adjacency, kernel, errors, warnings)
    _validate_circulation(request, adjacency, errors)
    _validate_stairs(request, kernel, errors, warnings)

    informational.append(
        _result(
            "phase9.vastu.integration",
            ValidationSeverity.INFO,
            "VASTU_VALIDATION_NOT_CLAIMED_WITHOUT_FROZEN_PRODUCTION_RULES",
        )
    )
    report = ValidationReport(
        valid=not errors,
        errors=_sort_results(errors),
        warnings=_sort_results(warnings),
        informational=_sort_results(informational),
    )
    result = ValidationRunResult(
        source_problem_hash=request.problem.compute_content_hash(),
        source_geometry_hash=request.geometry.compute_content_hash(),
        report=report,
    )
    return result.with_content_hash()
