"""Phase 7 deterministic OR-Tools CP-SAT rectangular planner."""

from .errors import PlannerError, SolverModelError, UnsupportedSolverProblemError
from .models import (
    SOLVER_MODEL_VERSION,
    ObjectiveContribution,
    PlannerBoundarySide,
    PlannerConfig,
    PlannerNotice,
    PlannerNoticeSeverity,
    PlannerResult,
    PlannerSearchVariant,
    PlannerStatus,
    ResidentialPlanningConfig,
    RoomPlacement,
    SolverRunMetadata,
)
from .rectangular_cp_sat import solve_rectangular_problem

__all__ = [
    "SOLVER_MODEL_VERSION",
    "ObjectiveContribution",
    "PlannerBoundarySide",
    "PlannerConfig",
    "PlannerError",
    "PlannerNotice",
    "PlannerNoticeSeverity",
    "PlannerResult",
    "PlannerSearchVariant",
    "PlannerStatus",
    "ResidentialPlanningConfig",
    "RoomPlacement",
    "SolverModelError",
    "SolverRunMetadata",
    "UnsupportedSolverProblemError",
    "solve_rectangular_problem",
]
