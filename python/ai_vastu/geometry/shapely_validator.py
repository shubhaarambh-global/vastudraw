from __future__ import annotations

from collections.abc import Iterable

from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.validation import explain_validity

from ai_vastu.plan_schema import AxisSegment, IntPolygon

from .errors import GeometryKernelDisagreementError, InvalidGeometryError
from .ring_math import total_area2
from .types import BooleanOperation


def to_shapely(polygon: IntPolygon) -> Polygon:
    return Polygon(
        [(p.x_mm, p.y_mm) for p in polygon.outer],
        holes=[[(p.x_mm, p.y_mm) for p in hole] for hole in polygon.holes],
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
