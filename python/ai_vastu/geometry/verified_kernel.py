from __future__ import annotations

from collections.abc import Iterable

from ai_vastu.plan_schema import IntPolygon

from .clipper_kernel import Clipper2GeometryKernel
from .shapely_validator import ShapelyGeometryValidator
from .types import BooleanOperation, GeometryResult


class VerifiedGeometryKernel:
    """Fail-closed facade: Clipper2 constructs; Shapely independently verifies."""

    def __init__(
        self,
        primary: Clipper2GeometryKernel | None = None,
        verifier: ShapelyGeometryValidator | None = None,
    ) -> None:
        self.primary = primary or Clipper2GeometryKernel()
        self.verifier = verifier or ShapelyGeometryValidator()

    def _boolean(
        self,
        operation: BooleanOperation,
        subjects: Iterable[IntPolygon],
        clips: Iterable[IntPolygon] = (),
    ) -> GeometryResult:
        subject_tuple = tuple(subjects)
        clip_tuple = tuple(clips)
        self.verifier.validate_all(subject_tuple)
        self.verifier.validate_all(clip_tuple)
        result = self.primary.boolean(operation, subject_tuple, clip_tuple)
        self.verifier.validate_all(result.polygons)
        self.verifier.verify_boolean(operation, subject_tuple, clip_tuple, result.polygons)
        return result

    def union(self, polygons: Iterable[IntPolygon]) -> GeometryResult:
        return self._boolean(BooleanOperation.UNION, polygons)

    def intersection(
        self, subjects: Iterable[IntPolygon], clips: Iterable[IntPolygon]
    ) -> GeometryResult:
        return self._boolean(BooleanOperation.INTERSECTION, subjects, clips)

    def difference(
        self, subjects: Iterable[IntPolygon], clips: Iterable[IntPolygon]
    ) -> GeometryResult:
        return self._boolean(BooleanOperation.DIFFERENCE, subjects, clips)

    def xor(self, subjects: Iterable[IntPolygon], clips: Iterable[IntPolygon]) -> GeometryResult:
        return self._boolean(BooleanOperation.XOR, subjects, clips)

    def offset(self, polygon: IntPolygon, delta_mm: int) -> GeometryResult:
        self.verifier.validate_polygon(polygon)
        result = self.primary.offset(polygon, delta_mm)
        self.verifier.validate_all(result.polygons)
        return result

    def contains(self, container: IntPolygon, candidate: IntPolygon) -> bool:
        self.verifier.validate_polygon(container)
        self.verifier.validate_polygon(candidate)
        result = self.primary.contains(container, candidate)
        self.verifier.verify_contains(container, candidate, result)
        return result

    def area2(self, polygon: IntPolygon) -> int:
        self.verifier.validate_polygon(polygon)
        return self.primary.area2(polygon)
