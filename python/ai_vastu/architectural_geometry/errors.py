class ArchitecturalGeometryError(ValueError):
    """Base failure for deterministic architectural geometry construction."""


class ArchitecturalGeometryInputError(ArchitecturalGeometryError):
    """Raised when source solver/constraint data cannot be constructed safely."""


class OpeningPlacementError(ArchitecturalGeometryError):
    """Raised when an explicit opening request cannot be attached to a wall."""


class StairConstructionError(ArchitecturalGeometryError):
    """Raised when an explicit stair request is incompatible with the solver room."""
