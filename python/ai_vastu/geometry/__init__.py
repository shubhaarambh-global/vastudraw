"""Deterministic integer-mm polygon geometry boundary."""

from .clipper_kernel import Clipper2GeometryKernel
from .errors import (
    GeometryError,
    GeometryKernelDisagreementError,
    InvalidGeometryError,
    NonIntegralGeometryError,
)
from .ring_math import area2_polygon, signed_area2_ring
from .shapely_validator import (
    ShapelyGeometryValidator,
    measure_site_partition,
    measure_site_residual_rectangles,
)
from .site_residuals import measure_site_residual_polygons, polygon_has_usable_core
from .types import (
    BooleanOperation,
    GeometryResult,
    MeasuredGeometryRegion,
    ResidualPolygonMeasurement,
    ResidualRectangleMeasurement,
    SitePartitionMeasurement,
    SiteResidualMeasurement,
    SiteResidualPolygonMeasurement,
)
from .verified_kernel import VerifiedGeometryKernel

__all__ = [
    "BooleanOperation",
    "Clipper2GeometryKernel",
    "GeometryError",
    "GeometryKernelDisagreementError",
    "GeometryResult",
    "InvalidGeometryError",
    "MeasuredGeometryRegion",
    "NonIntegralGeometryError",
    "ResidualPolygonMeasurement",
    "ResidualRectangleMeasurement",
    "ShapelyGeometryValidator",
    "SitePartitionMeasurement",
    "SiteResidualMeasurement",
    "SiteResidualPolygonMeasurement",
    "VerifiedGeometryKernel",
    "area2_polygon",
    "measure_site_partition",
    "measure_site_residual_polygons",
    "measure_site_residual_rectangles",
    "polygon_has_usable_core",
    "signed_area2_ring",
]
