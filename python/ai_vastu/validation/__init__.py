"""Deterministic architectural validation gate."""

from .models import (
    VALIDATOR_VERSION,
    ArchitecturalValidationRequest,
    DoorSwingContext,
    SwingSpace,
    ValidationConfig,
    ValidationRunResult,
)
from .validator import validate_architectural_geometry

__all__ = [
    "VALIDATOR_VERSION",
    "ArchitecturalValidationRequest",
    "DoorSwingContext",
    "SwingSpace",
    "ValidationConfig",
    "ValidationRunResult",
    "validate_architectural_geometry",
]
