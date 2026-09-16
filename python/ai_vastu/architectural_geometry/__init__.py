"""Phase 8 deterministic architectural geometry builder."""

from .builder import build_architectural_geometry
from .errors import (
    ArchitecturalGeometryError,
    ArchitecturalGeometryInputError,
    OpeningPlacementError,
    StairConstructionError,
)
from .models import (
    ARCHITECTURAL_GEOMETRY_VERSION,
    ArchitecturalGeometryRequest,
    ArchitecturalGeometryResult,
    GeometryNotice,
    GeometryNoticeSeverity,
    OpeningBuildRequest,
    StairBuildRequest,
    WallBuildConfig,
)

__all__ = [
    "ARCHITECTURAL_GEOMETRY_VERSION",
    "ArchitecturalGeometryError",
    "ArchitecturalGeometryInputError",
    "ArchitecturalGeometryRequest",
    "ArchitecturalGeometryResult",
    "GeometryNotice",
    "GeometryNoticeSeverity",
    "OpeningBuildRequest",
    "OpeningPlacementError",
    "StairBuildRequest",
    "StairConstructionError",
    "WallBuildConfig",
    "build_architectural_geometry",
]
