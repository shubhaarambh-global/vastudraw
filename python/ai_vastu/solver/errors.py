class PlannerError(ValueError):
    """Base error for deterministic CP-SAT planning."""


class UnsupportedSolverProblemError(PlannerError):
    """Raised when Phase 7 cannot model a problem without silently dropping semantics."""


class SolverModelError(PlannerError):
    """Raised when a problem cannot be converted into a valid CP-SAT model."""
