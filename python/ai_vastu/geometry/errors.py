from __future__ import annotations


class GeometryError(RuntimeError):
    """Base error for deterministic geometry operations."""


class InvalidGeometryError(GeometryError):
    """Raised when canonical polygon topology is invalid."""


class NonIntegralGeometryError(GeometryError):
    """Raised when the primary integer kernel returns non-millimetre coordinates."""


class GeometryKernelDisagreementError(GeometryError):
    """Raised when independent geometry verification disagrees with the primary kernel."""
