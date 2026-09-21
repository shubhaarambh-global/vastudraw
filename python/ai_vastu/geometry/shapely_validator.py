from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import explain_validity

from ai_vastu.plan_schema import AxisSegment, IntPolygon

from .errors import GeometryKernelDisagreementError, InvalidGeometryError
from .ring_math import total_area2
from .types import (
    BooleanOperation,
    MeasuredGeometryRegion,
    ResidualRectangleMeasurement,
    SitePartitionMeasurement,
    SiteResidualMeasurement,
)


def to_shapely(polygon: IntPolygon) -> Polygon:
    return Polygon(
        [(p.x_mm, p.y_mm) for p in polygon.outer],
        holes=[[(p.x_mm, p.y_mm) for p in hole] for hole in polygon.holes],
    )


def measure_site_partition(
    envelope: IntPolygon,
    classified_polygons: tuple[IntPolygon, ...],
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
                "Canonical classified geometry extends outside the confirmed "
                "buildable envelope."
            )

    if classified_shapes:
        classified_union = unary_union(classified_shapes)
        classified_union_area_mm2 = round(classified_union.area)
        residual_geometry = envelope_shape.difference(classified_union)
    else:
        classified_union_area_mm2 = 0
        residual_geometry = envelope_shape

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
    polygons = tuple(
        item for item in getattr(geometry, "geoms", ()) if isinstance(item, Polygon)
    )
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
                    round(polygon.boundary.intersection(road).length)
                    if road is not None
                    else 0
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
