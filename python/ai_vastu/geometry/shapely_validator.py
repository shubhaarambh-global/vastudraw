from __future__ import annotations

from collections.abc import Iterable
from math import hypot

from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import explain_validity

from ai_vastu.plan_schema import (
    AxisSegment,
    Floor,
    IntPoint,
    IntPolygon,
    OpeningKind,
    PlanDocument,
    Wall,
    WallCategory,
)

from .errors import (
    GeometryKernelDisagreementError,
    InvalidGeometryError,
    NonIntegralGeometryError,
)
from .ring_math import canonicalize_polygon, polygon_sort_key, total_area2
from .types import (
    BooleanOperation,
    MeasuredGeometryRegion,
    ResidualPolygonMeasurement,
    ResidualRectangleMeasurement,
    SitePartitionMeasurement,
    SiteResidualMeasurement,
    SiteResidualPolygonMeasurement,
)


def to_shapely(polygon: IntPolygon) -> Polygon:
    return Polygon(
        [(p.x_mm, p.y_mm) for p in polygon.outer],
        holes=[[(p.x_mm, p.y_mm) for p in hole] for hole in polygon.holes],
    )


def measure_site_partition(
    envelope: IntPolygon,
    classified_polygons: tuple[IntPolygon, ...],
    *,
    walls: tuple[Wall, ...] = (),
) -> SitePartitionMeasurement:
    """Measure a site partition without leaking Shapely types to callers."""

    envelope_shape = to_shapely(envelope)
    classified_shapes = tuple(to_shapely(polygon) for polygon in classified_polygons)
    for shape in (envelope_shape, *classified_shapes):
        if shape.is_empty or not shape.is_valid:
            raise ValueError("Site accounting requires valid non-empty polygons.")

    for shape in classified_shapes:
        if not envelope_shape.covers(shape):
            raise ValueError(
                "Canonical classified geometry extends outside the confirmed buildable envelope."
            )

    classified_union = unary_union(classified_shapes)
    base_classified_area_mm2 = round(classified_union.area)
    # Wall axes are canonical centre lines. Flat ends and the actual half
    # thickness describe material, without extending axes or filling voids.
    wall_shapes = tuple(
        LineString(
            [(wall.axis.start.x_mm, wall.axis.start.y_mm), (wall.axis.end.x_mm, wall.axis.end.y_mm)]
        ).buffer(wall.thickness_mm / 2, cap_style="flat")
        for wall in walls
    )
    wall_material = (
        unary_union(wall_shapes).intersection(envelope_shape).difference(classified_union)
    )
    classified_union = classified_union.union(wall_material)
    classified_union_area_mm2 = round(classified_union.area)
    # Quantize the partition consistently. Rounding wall area independently
    # can disagree by one mm2 with rounding the full union at half-mm edges.
    wall_material_area_mm2 = classified_union_area_mm2 - base_classified_area_mm2
    residual_geometry = envelope_shape.difference(classified_union)

    residual_polygons: tuple[Polygon, ...]
    if residual_geometry.is_empty:
        residual_polygons = ()
    elif isinstance(residual_geometry, Polygon):
        residual_polygons = (residual_geometry,)
    elif isinstance(residual_geometry, (MultiPolygon, GeometryCollection)):
        residual_polygons = tuple(
            geometry for geometry in residual_geometry.geoms if isinstance(geometry, Polygon)
        )
    else:
        residual_polygons = ()

    residual_regions: list[MeasuredGeometryRegion] = []
    for geometry in residual_polygons:
        area_mm2 = round(geometry.area)
        if area_mm2 <= 0:
            continue
        centroid = geometry.centroid
        min_x, min_y, max_x, max_y = geometry.bounds
        residual_regions.append(
            MeasuredGeometryRegion(
                area_mm2=area_mm2,
                centroid_x_mm=round(centroid.x),
                centroid_y_mm=round(centroid.y),
                min_x_mm=round(min_x),
                min_y_mm=round(min_y),
                max_x_mm=round(max_x),
                max_y_mm=round(max_y),
            )
        )

    return SitePartitionMeasurement(
        envelope_area_mm2=round(envelope_shape.area),
        classified_union_area_mm2=classified_union_area_mm2,
        classified_item_areas_mm2=tuple(round(shape.area) for shape in classified_shapes),
        wall_material_area_mm2=wall_material_area_mm2,
        residual_regions=tuple(
            sorted(
                residual_regions,
                key=lambda item: (
                    -item.area_mm2,
                    item.min_x_mm,
                    item.min_y_mm,
                    item.max_x_mm,
                    item.max_y_mm,
                ),
            )
        ),
    )


def _polygon_components(geometry: BaseGeometry) -> tuple[Polygon, ...]:
    if geometry.is_empty:
        return ()
    if isinstance(geometry, Polygon):
        return (geometry,)
    polygons = tuple(item for item in getattr(geometry, "geoms", ()) if isinstance(item, Polygon))
    return tuple(sorted(polygons, key=lambda item: item.bounds))


def _rectangle_bounds(polygon: Polygon) -> tuple[int, int, int, int] | None:
    if polygon.interiors:
        return None
    min_x, min_y, max_x, max_y = (round(value) for value in polygon.bounds)
    if min_x >= max_x or min_y >= max_y:
        return None
    rectangle = box(min_x, min_y, max_x, max_y)
    if polygon.symmetric_difference(rectangle).area > 1.0:
        return None
    return min_x, min_y, max_x, max_y


def _road_segment(
    envelope: Polygon,
    *,
    side: str,
    solver_step_mm: int,
) -> LineString:
    min_x, min_y, max_x, max_y = (round(value) for value in envelope.bounds)
    step = max(1, solver_step_mm)
    lattice_max_x = min_x + ((max_x - min_x) // step) * step
    lattice_max_y = min_y + ((max_y - min_y) // step) * step
    if side == "SOUTH":
        return LineString(((min_x, min_y), (max_x, min_y)))
    if side == "NORTH":
        return LineString(((min_x, lattice_max_y), (max_x, lattice_max_y)))
    if side == "WEST":
        return LineString(((min_x, min_y), (min_x, max_y)))
    if side == "EAST":
        return LineString(((lattice_max_x, min_y), (lattice_max_x, max_y)))
    raise ValueError(f"Unsupported road boundary side: {side!r}.")


def measure_site_residual_rectangles(
    envelope: IntPolygon,
    occupied_polygons: tuple[IntPolygon, ...],
    *,
    road_boundary_side: str | None,
    solver_step_mm: int,
) -> SiteResidualMeasurement:
    """Measure rectangular residual candidates without exposing vendor geometry."""

    envelope_shape = to_shapely(envelope)
    occupied_shapes = tuple(to_shapely(polygon) for polygon in occupied_polygons)
    occupied = unary_union(occupied_shapes) if occupied_shapes else None
    residual = envelope_shape.difference(occupied) if occupied is not None else envelope_shape
    road = (
        _road_segment(
            envelope_shape,
            side=road_boundary_side,
            solver_step_mm=solver_step_mm,
        )
        if road_boundary_side is not None
        else None
    )

    road_adjacent = (
        tuple(
            index
            for index, shape in enumerate(occupied_shapes)
            if shape.boundary.intersection(road).length > 0
        )
        if road is not None
        else ()
    )
    rectangles: list[ResidualRectangleMeasurement] = []
    for polygon in _polygon_components(residual):
        bounds = _rectangle_bounds(polygon)
        if bounds is None:
            continue
        rectangles.append(
            ResidualRectangleMeasurement(
                bounds=bounds,
                area_mm2=round(polygon.area),
                touches_envelope_boundary=(
                    polygon.boundary.intersection(envelope_shape.boundary).length > 0
                ),
                road_boundary_shared_length_mm=(
                    round(polygon.boundary.intersection(road).length) if road is not None else 0
                ),
                adjacent_polygon_indexes=tuple(
                    index
                    for index, shape in enumerate(occupied_shapes)
                    if polygon.boundary.intersection(shape.boundary).length > 0
                ),
            )
        )

    return SiteResidualMeasurement(
        envelope_area_mm2=round(envelope_shape.area),
        rectangles=tuple(rectangles),
        road_adjacent_polygon_indexes=road_adjacent,
    )


def _integral_coordinate(value: float) -> int:
    rounded = round(value)
    if abs(value - rounded) > 1e-9:
        raise NonIntegralGeometryError(
            f"Residual-site measurement produced a non-integral millimetre coordinate {value!r}."
        )
    return int(rounded)


def _int_ring(
    coordinates: Iterable[tuple[float, ...]],
) -> tuple[IntPoint, ...]:
    raw = list(coordinates)
    if len(raw) >= 2 and raw[0] == raw[-1]:
        raw = raw[:-1]

    points: list[IntPoint] = []
    for coordinate in raw:
        if len(coordinate) < 2:
            raise NonIntegralGeometryError(
                "Residual-site measurement produced an incomplete polygon coordinate."
            )
        x, y = coordinate[0], coordinate[1]
        point = IntPoint(
            x_mm=_integral_coordinate(float(x)),
            y_mm=_integral_coordinate(float(y)),
        )
        if points and point == points[-1]:
            continue
        points.append(point)

    if len(points) >= 2 and points[0] == points[-1]:
        points.pop()

    if len(points) < 3:
        raise NonIntegralGeometryError(
            "Residual-site measurement produced a degenerate polygon ring."
        )

    return tuple(points)


def _int_polygon(polygon: Polygon) -> IntPolygon:
    result = canonicalize_polygon(
        IntPolygon(
            outer=_int_ring(polygon.exterior.coords),
            holes=tuple(_int_ring(interior.coords) for interior in polygon.interiors),
        )
    )

    rebuilt = to_shapely(result)
    if not rebuilt.is_valid:
        raise ValueError("Residual-site measurement produced invalid canonical geometry.")

    disagreement_area = rebuilt.symmetric_difference(polygon).area
    if disagreement_area > 1e-7:
        raise NonIntegralGeometryError(
            "Residual-site geometry cannot be represented exactly on the integer-mm lattice; "
            f"disagreement area={disagreement_area:.9f} mm2."
        )

    return result


def polygon_has_usable_core_shapely(
    polygon: IntPolygon,
    *,
    minimum_width_mm: int,
) -> bool:
    """Vendor-adapter implementation of the purposeful-space core predicate."""

    if minimum_width_mm <= 0:
        raise ValueError("minimum_width_mm must be positive.")

    shape = to_shapely(polygon)
    inset_mm = max(1, minimum_width_mm // 2 - 1)
    core = shape.buffer(-inset_mm, join_style="mitre")
    return not core.is_empty and core.area > 0


def measure_site_residual_polygons_shapely(
    envelope: IntPolygon,
    occupied_polygons: tuple[IntPolygon, ...],
    *,
    road_boundary_side: str | None,
    solver_step_mm: int,
) -> SiteResidualPolygonMeasurement:
    """Measure exact residual components inside the Shapely/GEOS adapter boundary.

    Purposeful-site derivation uses the same residual construction as site
    accounting. Result coordinates must remain exactly representable on the
    integer-mm lattice; otherwise the adapter fails closed.
    """

    envelope_shape = to_shapely(envelope)
    occupied_shapes = tuple(to_shapely(polygon) for polygon in occupied_polygons)

    for shape in (envelope_shape, *occupied_shapes):
        if shape.is_empty or not shape.is_valid:
            raise ValueError("Residual-site measurement requires valid non-empty polygons.")

    for shape in occupied_shapes:
        if not envelope_shape.covers(shape):
            raise ValueError(
                "Canonical occupied geometry extends outside the confirmed buildable envelope."
            )

    occupied = unary_union(occupied_shapes) if occupied_shapes else None
    residual = envelope_shape.difference(occupied) if occupied is not None else envelope_shape

    road = (
        _road_segment(
            envelope_shape,
            side=road_boundary_side,
            solver_step_mm=solver_step_mm,
        )
        if road_boundary_side is not None
        else None
    )

    road_adjacent = (
        tuple(
            index
            for index, shape in enumerate(occupied_shapes)
            if shape.boundary.intersection(road).length > 0
        )
        if road is not None
        else ()
    )

    measurements: list[ResidualPolygonMeasurement] = []

    for residual_shape in _polygon_components(residual):
        if residual_shape.area <= 0:
            continue

        polygon = _int_polygon(residual_shape)
        shape = to_shapely(polygon)
        min_x, min_y, max_x, max_y = (round(value) for value in shape.bounds)

        measurements.append(
            ResidualPolygonMeasurement(
                polygon=polygon,
                bounds=(min_x, min_y, max_x, max_y),
                rectangle_bounds=_rectangle_bounds(shape),
                area_mm2=round(shape.area),
                touches_envelope_boundary=(
                    shape.boundary.intersection(envelope_shape.boundary).length > 0
                ),
                road_boundary_shared_length_mm=(
                    round(shape.boundary.intersection(road).length) if road is not None else 0
                ),
                adjacent_polygon_indexes=tuple(
                    index
                    for index, occupied_shape in enumerate(occupied_shapes)
                    if shape.boundary.intersection(occupied_shape.boundary).length > 0
                ),
            )
        )

    measurements.sort(
        key=lambda item: (
            polygon_sort_key(item.polygon),
            item.area_mm2,
        )
    )

    return SiteResidualPolygonMeasurement(
        envelope_area_mm2=round(envelope_shape.area),
        polygons=tuple(measurements),
        road_adjacent_polygon_indexes=road_adjacent,
    )


class ShapelyGeometryValidator:
    """Independent floating-point topology validator based on Shapely/GEOS."""

    def validate_polygon(self, polygon: IntPolygon) -> None:
        geometry = to_shapely(polygon)
        if geometry.is_empty or geometry.area <= 0:
            raise InvalidGeometryError("Polygon has zero/negative usable area.")
        if not geometry.is_valid:
            raise InvalidGeometryError(f"Invalid polygon topology: {explain_validity(geometry)}")

    def validate_all(self, polygons: Iterable[IntPolygon]) -> None:
        for polygon in polygons:
            self.validate_polygon(polygon)

    def covers_axis_segment(self, container: IntPolygon, segment: AxisSegment) -> bool:
        line = LineString(
            [
                (segment.start.x_mm, segment.start.y_mm),
                (segment.end.x_mm, segment.end.y_mm),
            ]
        )
        return bool(to_shapely(container).covers(line))

    @staticmethod
    def _union(polygons: Iterable[IntPolygon]) -> BaseGeometry:
        geometries = [to_shapely(polygon) for polygon in polygons]
        if not geometries:
            return Polygon()
        return unary_union(geometries)

    def verify_boolean(
        self,
        operation: BooleanOperation,
        subjects: tuple[IntPolygon, ...],
        clips: tuple[IntPolygon, ...],
        output: tuple[IntPolygon, ...],
    ) -> None:
        subject = self._union(subjects)
        clip = self._union(clips)
        if operation is BooleanOperation.UNION:
            expected = subject
        elif operation is BooleanOperation.INTERSECTION:
            expected = subject.intersection(clip)
        elif operation is BooleanOperation.DIFFERENCE:
            expected = subject.difference(clip)
        elif operation is BooleanOperation.XOR:
            expected = subject.symmetric_difference(clip)
        else:  # pragma: no cover
            raise AssertionError(operation)

        actual = self._union(output)
        disagreement_area = expected.symmetric_difference(actual).area
        if disagreement_area > 1e-7:
            raise GeometryKernelDisagreementError(
                f"Clipper2/Shapely boolean disagreement area={disagreement_area:.9f} mm²."
            )

        # Independent area parity in doubled-mm² units.
        expected_area2 = round(expected.area * 2)
        actual_area2 = total_area2(output)
        if expected_area2 != actual_area2:
            raise GeometryKernelDisagreementError(
                "Clipper2/Shapely area disagreement: "
                f"{actual_area2} vs {expected_area2} doubled mm²."
            )

    def verify_contains(self, container: IntPolygon, candidate: IntPolygon, actual: bool) -> None:
        expected = to_shapely(container).covers(to_shapely(candidate))
        if expected != actual:
            raise GeometryKernelDisagreementError(
                f"Clipper2/Shapely containment disagreement: primary={actual}, verifier={expected}."
            )


def _route_crosses_wall(floor: Floor, route: Polygon) -> bool:
    if route.area == 0:
        return False
    for wall in floor.walls:
        a, b = wall.axis.start, wall.axis.end
        length = hypot(b.x_mm - a.x_mm, b.y_mm - a.y_mm)
        if not length:
            continue
        gaps = sorted(
            (
                opening.offset_from_wall_start_mm,
                opening.offset_from_wall_start_mm + opening.width_mm,
            )
            for opening in floor.openings
            if opening.wall_id == wall.id
            and opening.kind is OpeningKind.OPENING
            and opening.sill_height_mm == 0
            and opening.height_mm >= 2100
        )
        cursor = 0.0
        for lo, hi in (*gaps, (length, length)):
            if lo > cursor:
                segment = LineString(
                    (
                        (
                            a.x_mm + (b.x_mm - a.x_mm) * cursor / length,
                            a.y_mm + (b.y_mm - a.y_mm) * cursor / length,
                        ),
                        (
                            a.x_mm + (b.x_mm - a.x_mm) * lo / length,
                            a.y_mm + (b.y_mm - a.y_mm) * lo / length,
                        ),
                    )
                )
                if route.intersection(segment).difference(route.boundary).length > 0:
                    return True
            cursor = max(cursor, hi)
    return False


def measure_vehicle_access_failures(document: PlanDocument) -> tuple[str, ...]:
    """Return bounded failures; vehicle routes never traverse occupied rooms.

    An existing OPENING is an unobstructed, full-height wall gap, so vehicle
    clearance needs no new schema kind or reinterpretation of a pedestrian door.
    """
    road_ids = {edge for road in document.roads for edge in road.plot_edge_ids}
    plot = document.plot.boundary.outer
    site = Polygon(
        [(point.x_mm, point.y_mm) for point in plot],
        holes=[
            [(point.x_mm, point.y_mm) for point in ring] for ring in document.plot.boundary.holes
        ],
    )
    roads = tuple(
        (plot[index], plot[(index + 1) % len(plot)])
        for index, edge_id in enumerate(document.plot.edge_ids)
        if edge_id in road_ids
    )
    failures: list[str] = []
    for floor in document.floors:
        parking = tuple(
            room for room in floor.rooms if room.room_type.value in {"parking", "garage"}
        )
        if not parking:
            continue
        if floor.index != 0:
            failures.append("VEHICLE_ACCESS_NOT_GROUND")
            continue
        walls = {wall.id: wall for wall in floor.walls}
        for bay in parking:
            bay_polygon = Polygon([(point.x_mm, point.y_mm) for point in bay.polygon.outer])
            if bay.polygon.holes or not bay_polygon.equals(bay_polygon.envelope):
                failures.append("VEHICLE_ACCESS_INVALID")
                continue
            if _route_crosses_wall(floor, bay_polygon) or any(
                room.id != bay.id
                and bay_polygon.intersection(
                    Polygon(
                        [(point.x_mm, point.y_mm) for point in room.polygon.outer],
                        holes=[
                            [(point.x_mm, point.y_mm) for point in ring]
                            for ring in room.polygon.holes
                        ],
                    )
                ).area > 0
                for room in floor.rooms
            ):
                failures.append("VEHICLE_ACCESS_INVALID")
                continue
            min_x, min_y, max_x, max_y = bay_polygon.bounds
            insets = {"west": 0.0, "east": 0.0, "south": 0.0, "north": 0.0}
            for boundary_wall in floor.walls:
                a, b = boundary_wall.axis.start, boundary_wall.axis.end
                if a.x_mm == b.x_mm and max(a.y_mm, b.y_mm) > min_y and min(a.y_mm, b.y_mm) < max_y:
                    side = "west" if a.x_mm == min_x else "east" if a.x_mm == max_x else None
                elif (
                    a.y_mm == b.y_mm and max(a.x_mm, b.x_mm) > min_x and min(a.x_mm, b.x_mm) < max_x
                ):
                    side = "south" if a.y_mm == min_y else "north" if a.y_mm == max_y else None
                else:
                    side = None
                if side is not None:
                    insets[side] = max(insets[side], boundary_wall.thickness_mm / 2)
            clear_width = max_x - min_x - insets["west"] - insets["east"]
            clear_depth = max_y - min_y - insets["south"] - insets["north"]
            usable = False
            for opening in floor.openings:
                wall = walls.get(opening.wall_id)
                if (
                    wall is None
                    or wall.category is not WallCategory.EXTERNAL
                    or opening.kind is not OpeningKind.OPENING
                    or opening.width_mm < 3000
                    or opening.height_mm < 2100
                    or opening.sill_height_mm != 0
                ):
                    continue
                a, b = wall.axis.start, wall.axis.end
                horizontal = a.y_mm == b.y_mm
                vertical = a.x_mm == b.x_mm
                if not horizontal and not vertical:
                    continue
                if (horizontal and (clear_width < 3000 or clear_depth < 5500)) or (
                    vertical and (clear_depth < 3000 or clear_width < 5500)
                ):
                    continue
                length = abs(b.x_mm - a.x_mm) + abs(b.y_mm - a.y_mm)
                offset = opening.offset_from_wall_start_mm
                if offset < 0 or offset + opening.width_mm > length:
                    continue
                sign = 1 if (b.x_mm > a.x_mm if horizontal else b.y_mm > a.y_mm) else -1
                start = (
                    (a.x_mm + sign * offset, a.y_mm)
                    if horizontal
                    else (a.x_mm, a.y_mm + sign * offset)
                )
                end = (
                    (start[0] + sign * opening.width_mm, start[1])
                    if horizontal
                    else (start[0], start[1] + sign * opening.width_mm)
                )
                boundary_contact = bay_polygon.boundary.intersection(LineString((start, end)))
                if boundary_contact.length < opening.width_mm:
                    continue
                for road_start, road_end in roads:
                    if horizontal:
                        if road_start.y_mm != road_end.y_mm:
                            continue
                        lo, hi = sorted((road_start.x_mm, road_end.x_mm))
                        if min(start[0], end[0]) < lo or max(start[0], end[0]) > hi:
                            continue
                        road_fixed, wall_fixed = road_start.y_mm, a.y_mm
                        centre = bay_polygon.centroid.y
                        projected = ((end[0], road_fixed), (start[0], road_fixed))
                    else:
                        if road_start.x_mm != road_end.x_mm:
                            continue
                        lo, hi = sorted((road_start.y_mm, road_end.y_mm))
                        if min(start[1], end[1]) < lo or max(start[1], end[1]) > hi:
                            continue
                        road_fixed, wall_fixed = road_start.x_mm, a.x_mm
                        centre = bay_polygon.centroid.x
                        projected = ((road_fixed, end[1]), (road_fixed, start[1]))
                    if (road_fixed - wall_fixed) * (centre - wall_fixed) > 0:
                        continue
                    route = Polygon((start, end, *projected))
                    if route.area > 0 and not site.covers(route):
                        continue
                    if _route_crosses_wall(floor, route):
                        continue
                    if any(
                        room.id != bay.id
                        and route.intersection(
                            Polygon([(point.x_mm, point.y_mm) for point in room.polygon.outer])
                        ).area
                        > 0
                        for room in floor.rooms
                    ):
                        continue
                    usable = True
                    break
                if usable:
                    break
            if not usable:
                failures.append("VEHICLE_ACCESS_INVALID")
    return tuple(failures)
