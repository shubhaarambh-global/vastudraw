class ScoringError(RuntimeError):
    """Base class for deterministic scoring failures."""


class ScoringInputError(ScoringError):
    """Raised when a candidate pool violates Phase 10 scoring preconditions."""
