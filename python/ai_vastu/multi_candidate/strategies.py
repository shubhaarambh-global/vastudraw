from __future__ import annotations

from ai_vastu.solver import PlannerSearchVariant

from .models import CandidateStrategy, CandidateStrategyKind


def default_candidate_strategies() -> tuple[CandidateStrategy, ...]:
    """Stable Phase 26C strategy catalogue.

    26C.2 uses the labels to select deterministic search diversification only.
    A label is never treated as evidence that an unmeasured quality improved.
    """

    return (
        CandidateStrategy(
            strategy_id="compact",
            kind=CandidateStrategyKind.COMPACT,
            label="Compact",
            description="Deterministic lower-left search with measured scoring after validation.",
            deterministic_ordinal=0,
        ),
        CandidateStrategy(
            strategy_id="privacy",
            kind=CandidateStrategyKind.PRIVACY,
            label="Privacy-first",
            description=(
                "Deterministic upper-right search variant; privacy remains unmeasured "
                "until geometric privacy evidence exists."
            ),
            deterministic_ordinal=1,
        ),
        CandidateStrategy(
            strategy_id="daylight",
            kind=CandidateStrategyKind.DAYLIGHT,
            label="Daylight",
            description=(
                "Deterministic upper-left search variant; daylight improvement is not claimed "
                "without measurable opening or perimeter evidence."
            ),
            deterministic_ordinal=2,
        ),
        CandidateStrategy(
            strategy_id="circulation",
            kind=CandidateStrategyKind.CIRCULATION,
            label="Circulation",
            description=(
                "Deterministic lower-right search variant with existing adjacency "
                "and circulation validation retained."
            ),
            deterministic_ordinal=3,
        ),
        CandidateStrategy(
            strategy_id="vastu-aware",
            kind=CandidateStrategyKind.VASTU_AWARE,
            label="Vastu-aware",
            description=(
                "Reverse-order deterministic search; ranking uses the actual soft-Vastu "
                "geometry assessment rather than the strategy label."
            ),
            deterministic_ordinal=4,
        ),
        CandidateStrategy(
            strategy_id="alternate-topology",
            kind=CandidateStrategyKind.ALTERNATE_TOPOLOGY,
            label="Alternate zoning",
            description=(
                "Reverse-order upper-right search intended to expose another deterministic "
                "placement topology when the constraint space permits."
            ),
            deterministic_ordinal=5,
        ),
    )


_SEARCH_VARIANTS: dict[CandidateStrategyKind, PlannerSearchVariant] = {
    CandidateStrategyKind.COMPACT: PlannerSearchVariant.LOWER_LEFT,
    CandidateStrategyKind.PRIVACY: PlannerSearchVariant.UPPER_RIGHT,
    CandidateStrategyKind.DAYLIGHT: PlannerSearchVariant.UPPER_LEFT,
    CandidateStrategyKind.CIRCULATION: PlannerSearchVariant.LOWER_RIGHT,
    CandidateStrategyKind.VASTU_AWARE: PlannerSearchVariant.REVERSE_LOWER_LEFT,
    CandidateStrategyKind.ALTERNATE_TOPOLOGY: PlannerSearchVariant.REVERSE_UPPER_RIGHT,
}


def search_variant_for_strategy(strategy: CandidateStrategy) -> PlannerSearchVariant:
    return _SEARCH_VARIANTS[strategy.kind]
