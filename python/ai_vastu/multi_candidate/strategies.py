from __future__ import annotations

from .models import CandidateStrategy, CandidateStrategyKind


def default_candidate_strategies() -> tuple[CandidateStrategy, ...]:
    """Deterministic strategy catalogue for Phase 26C.

    26C.1 defines the stable strategy identities and UI contract.
    Actual solver diversification is implemented in 26C.2.
    """

    return (
        CandidateStrategy(
            strategy_id="compact",
            kind=CandidateStrategyKind.COMPACT,
            label="Compact",
            description="Prioritize efficient area use and reduced dead circulation.",
            deterministic_ordinal=0,
        ),
        CandidateStrategy(
            strategy_id="privacy",
            kind=CandidateStrategyKind.PRIVACY,
            label="Privacy-first",
            description="Prioritize bedroom privacy and controlled sightlines.",
            deterministic_ordinal=1,
        ),
        CandidateStrategy(
            strategy_id="daylight",
            kind=CandidateStrategyKind.DAYLIGHT,
            label="Daylight",
            description=(
                "Prioritize daylight and ventilation opportunities "
                "without relaxing hard constraints."
            ),
            deterministic_ordinal=2,
        ),
        CandidateStrategy(
            strategy_id="circulation",
            kind=CandidateStrategyKind.CIRCULATION,
            label="Circulation",
            description="Prioritize direct access, adjacency quality and simpler movement paths.",
            deterministic_ordinal=3,
        ),
        CandidateStrategy(
            strategy_id="vastu-aware",
            kind=CandidateStrategyKind.VASTU_AWARE,
            label="Vastu-aware",
            description=(
                "Explore a valid architectural option that can rank well under soft Vastu guidance."
            ),
            deterministic_ordinal=4,
        ),
        CandidateStrategy(
            strategy_id="alternate-topology",
            kind=CandidateStrategyKind.ALTERNATE_TOPOLOGY,
            label="Alternate zoning",
            description="Explore a materially different deterministic zoning interpretation.",
            deterministic_ordinal=5,
        ),
    )
