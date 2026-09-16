"""Phase 7 deterministic OR-Tools CP-SAT rectangular planner."""

from .errors import PlannerError, SolverModelError, UnsupportedSolverProblemError
from .models import (
    SOLVER_MODEL_VERSION,
    ObjectiveContribution,
    PlannerConfig,
    PlannerNotice,
    PlannerNoticeSeverity,
    PlannerResult,
    PlannerStatus,
    RoomPlacement,
    SolverRunMetadata,
)
from .rectangular_cp_sat import solve_rectangular_problem

__all__ = [
    "SOLVER_MODEL_VERSION",
    "ObjectiveContribution",
    "PlannerConfig",
    "PlannerError",
    "PlannerNotice",
    "PlannerNoticeSeverity",
    "PlannerResult",
    "PlannerStatus",
    "RoomPlacement",
    "SolverModelError",
    "SolverRunMetadata",
    "UnsupportedSolverProblemError",
    "solve_rectangular_problem",
]
