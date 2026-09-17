from ai_vastu.multi_candidate import (
    PHASE26C_VERSION,
    default_candidate_strategies,
    search_variant_for_strategy,
)
from ai_vastu.solver import PlannerSearchVariant


def test_phase26c2_has_six_stable_search_variants() -> None:
    strategies = default_candidate_strategies()
    variants = tuple(search_variant_for_strategy(item) for item in strategies)

    assert PHASE26C_VERSION == "26C.2"
    assert len(strategies) == 6
    assert len(set(variants)) == 6
    assert variants == (
        PlannerSearchVariant.LOWER_LEFT,
        PlannerSearchVariant.UPPER_RIGHT,
        PlannerSearchVariant.UPPER_LEFT,
        PlannerSearchVariant.LOWER_RIGHT,
        PlannerSearchVariant.REVERSE_LOWER_LEFT,
        PlannerSearchVariant.REVERSE_UPPER_RIGHT,
    )


def test_strategy_descriptions_do_not_claim_unmeasured_improvement() -> None:
    by_id = {item.strategy_id: item for item in default_candidate_strategies()}

    assert "unmeasured" in by_id["privacy"].description
    assert "not claimed" in by_id["daylight"].description
    assert "actual soft-Vastu" in by_id["vastu-aware"].description
