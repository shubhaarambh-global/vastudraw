class ConstraintCompilerError(ValueError):
    """Base error for deterministic requirement compilation."""


class ConstraintConflictError(ConstraintCompilerError):
    """Raised when user requirements are internally contradictory."""


class ConstraintInfeasibleError(ConstraintCompilerError):
    """Raised when simple exact preflight checks prove the problem infeasible."""
