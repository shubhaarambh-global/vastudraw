class OrientationError(ValueError):
    """Base error for deterministic direction/orientation failures."""


class AmbiguousRoadFacingError(OrientationError):
    """Raised when one road spans edges that do not share one 8-way facing direction."""
