"""Deterministic integer-mm polygon geometry boundary."""

from .clipper_kernel import Clipper2GeometryKernel
from .errors import (
    GeometryError,
    GeometryKernelDisagreementError,
    InvalidGeometryError,
    NonIntegralGeometryError,
)
from .ring_math import area2_polygon, signed_area2_ring
from .shapely_validator import ShapelyGeometryValidator
from .types import BooleanOperation, GeometryResult
from .verified_kernel import VerifiedGeometryKernel

__all__ = [
    "BooleanOperation",
    "Clipper2GeometryKernel",
    "GeometryError",
    "GeometryKernelDisagreementError",
    "GeometryResult",
    "InvalidGeometryError",
    "NonIntegralGeometryError",
    "ShapelyGeometryValidator",
    "VerifiedGeometryKernel",
    "area2_polygon",
    "signed_area2_ring",
]
