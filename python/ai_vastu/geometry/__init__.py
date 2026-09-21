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
from .types import (
    BooleanOperation,
    GeometryResult,
    MeasuredGeometryRegion,
    ResidualRectangleMeasurement,
    SitePartitionMeasurement,
    SiteResidualMeasurement,
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
    "ResidualRectangleMeasurement",
    "ShapelyGeometryValidator",
    "SitePartitionMeasurement",
    "SiteResidualMeasurement",
    "VerifiedGeometryKernel",
    "area2_polygon",
    "measure_site_partition",
    "measure_site_residual_rectangles",
    "signed_area2_ring",
]
