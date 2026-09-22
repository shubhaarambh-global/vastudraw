from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_vastu.plan_schema import IntPolygon


class BooleanOperation(StrEnum):
    UNION = "union"
    INTERSECTION = "intersection"
    DIFFERENCE = "difference"
    XOR = "xor"


@dataclass(frozen=True, slots=True)
class GeometryResult:
    polygons: tuple[IntPolygon, ...]

    @property
    def is_empty(self) -> bool:
        return not self.polygons


@dataclass(frozen=True, slots=True)
class MeasuredGeometryRegion:
    area_mm2: int
    centroid_x_mm: int
    centroid_y_mm: int
    min_x_mm: int
    min_y_mm: int
    max_x_mm: int
    max_y_mm: int


@dataclass(frozen=True, slots=True)
class SitePartitionMeasurement:
    envelope_area_mm2: int
    classified_union_area_mm2: int
    classified_item_areas_mm2: tuple[int, ...]
    residual_regions: tuple[MeasuredGeometryRegion, ...]


@dataclass(frozen=True, slots=True)
class ResidualRectangleMeasurement:
    bounds: tuple[int, int, int, int]
    area_mm2: int
    touches_envelope_boundary: bool
    road_boundary_shared_length_mm: int
    adjacent_polygon_indexes: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SiteResidualMeasurement:
    envelope_area_mm2: int
    rectangles: tuple[ResidualRectangleMeasurement, ...]
    road_adjacent_polygon_indexes: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ResidualPolygonMeasurement:
    polygon: IntPolygon
    bounds: tuple[int, int, int, int]
    rectangle_bounds: tuple[int, int, int, int] | None
    area_mm2: int
    touches_envelope_boundary: bool
    road_boundary_shared_length_mm: int
    adjacent_polygon_indexes: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SiteResidualPolygonMeasurement:
    envelope_area_mm2: int
    polygons: tuple[ResidualPolygonMeasurement, ...]
    road_adjacent_polygon_indexes: tuple[int, ...]
