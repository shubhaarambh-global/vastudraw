from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar

import pyclipr  # type: ignore[import-untyped]

from ai_vastu.plan_schema import IntPolygon

from .conversion import paths_to_polygons, polygon_to_paths
from .ring_math import area2_polygon
from .types import BooleanOperation, GeometryResult


class Clipper2GeometryKernel:
    """Primary polygon kernel using Clipper2 through the pyclipr adapter.

    Canonical coordinates are already integer millimetres, so scaleFactor is deliberately 1.
    No vendor type escapes this adapter.
    """

    _OP_MAP: ClassVar[dict[BooleanOperation, Any]] = {
        BooleanOperation.UNION: pyclipr.Union,
        BooleanOperation.INTERSECTION: pyclipr.Intersection,
        BooleanOperation.DIFFERENCE: pyclipr.Difference,
        BooleanOperation.XOR: pyclipr.Xor,
    }

    @staticmethod
    def _flatten(polygons: Iterable[IntPolygon]) -> list[list[tuple[int, int]]]:
        paths: list[list[tuple[int, int]]] = []
        for polygon in polygons:
            paths.extend(polygon_to_paths(polygon))
        return paths

    def boolean(
        self,
        operation: BooleanOperation,
        subjects: Iterable[IntPolygon],
        clips: Iterable[IntPolygon] = (),
    ) -> GeometryResult:
        subject_paths = self._flatten(subjects)
        clip_paths = self._flatten(clips)
        if not subject_paths:
            return GeometryResult(())

        clipper = pyclipr.Clipper()
        clipper.scaleFactor = 1
        clipper.addPaths(subject_paths, pyclipr.Subject, False)
        if clip_paths:
            clipper.addPaths(clip_paths, pyclipr.Clip, False)
        output = clipper.execute(self._OP_MAP[operation], pyclipr.FillRule.NonZero)
        return GeometryResult(paths_to_polygons(output))

    def union(self, polygons: Iterable[IntPolygon]) -> GeometryResult:
        return self.boolean(BooleanOperation.UNION, polygons)

    def intersection(
        self, subjects: Iterable[IntPolygon], clips: Iterable[IntPolygon]
    ) -> GeometryResult:
        return self.boolean(BooleanOperation.INTERSECTION, subjects, clips)

    def difference(
        self, subjects: Iterable[IntPolygon], clips: Iterable[IntPolygon]
    ) -> GeometryResult:
        return self.boolean(BooleanOperation.DIFFERENCE, subjects, clips)

    def xor(self, subjects: Iterable[IntPolygon], clips: Iterable[IntPolygon]) -> GeometryResult:
        return self.boolean(BooleanOperation.XOR, subjects, clips)

    def offset(self, polygon: IntPolygon, delta_mm: int) -> GeometryResult:
        if delta_mm == 0:
            return GeometryResult((polygon,))
        offsetter = pyclipr.ClipperOffset()
        offsetter.scaleFactor = 1
        offsetter.addPaths(
            polygon_to_paths(polygon), pyclipr.JoinType.Miter, pyclipr.EndType.Polygon
        )
        output = offsetter.execute(delta_mm)
        return GeometryResult(paths_to_polygons(output))

    def contains(self, container: IntPolygon, candidate: IntPolygon) -> bool:
        remainder = self.difference((candidate,), (container,))
        return remainder.is_empty

    @staticmethod
    def area2(polygon: IntPolygon) -> int:
        return area2_polygon(polygon)
