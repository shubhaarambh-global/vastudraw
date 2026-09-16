"""Deterministic scoring and diverse alternative selection."""

from .errors import ScoringError, ScoringInputError
from .evaluator import score_candidate
from .models import (
    SCORING_VERSION,
    CandidateScore,
    ExcludedAlternative,
    ObjectiveScore,
    RankedAlternative,
    ScoringCandidate,
    ScoringConfig,
    ScoringNotice,
    ScoringNoticeSeverity,
    ScoringRequest,
    ScoringRunResult,
)
from .selector import score_and_select_alternatives

__all__ = [
    "SCORING_VERSION",
    "CandidateScore",
    "ExcludedAlternative",
    "ObjectiveScore",
    "RankedAlternative",
    "ScoringCandidate",
    "ScoringConfig",
    "ScoringError",
    "ScoringInputError",
    "ScoringNotice",
    "ScoringNoticeSeverity",
    "ScoringRequest",
    "ScoringRunResult",
    "score_and_select_alternatives",
    "score_candidate",
]
