from __future__ import annotations

from ai_vastu.vastu_reasoning import load_soft_vastu_catalog


def test_catalog_is_source_backed_and_never_hard() -> None:
    catalog = load_soft_vastu_catalog()
    assert catalog.hard_constraints_allowed is False
    assert len(catalog.sources) >= 4
    assert len(catalog.rules) >= 10
    assert all(rule.hard_constraint is False for rule in catalog.rules)
    assert any(rule.source_disagreement for rule in catalog.rules)


def test_core_non_adjustable_rules_are_explicit() -> None:
    catalog = load_soft_vastu_catalog()
    by_id = {rule.rule_id: rule for rule in catalog.rules}
    assert by_id["SOFT_PUJA_ZONE"].reasoning_adjustable is False
    assert by_id["SOFT_KITCHEN_ZONE"].reasoning_adjustable is False
