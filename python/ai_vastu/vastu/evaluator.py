from __future__ import annotations

from collections.abc import Iterable

from ai_vastu.plan_schema.models import VastuStatus

from .models import (
    BooleanPredicate,
    EnumSetPredicate,
    NumericRangePredicate,
    RuleBundle,
    RuleEvaluation,
    VastuFact,
    VastuRule,
)


def _predicate_passes(rule: VastuRule, fact: VastuFact) -> bool:
    predicate = rule.predicate
    value = fact.value

    if isinstance(predicate, NumericRangePredicate):
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        if predicate.minimum_inclusive is not None and value < predicate.minimum_inclusive:
            return False
        return predicate.maximum_inclusive is None or value <= predicate.maximum_inclusive

    if isinstance(predicate, EnumSetPredicate):
        return isinstance(value, str) and value in predicate.allowed_values

    if isinstance(predicate, BooleanPredicate):
        return isinstance(value, bool) and value is predicate.expected

    return False


def evaluate_rule(rule: VastuRule, facts: Iterable[VastuFact]) -> tuple[RuleEvaluation, ...]:
    matching = tuple(
        fact
        for fact in facts
        if fact.matches_subject(rule.subject)
        and fact.geometry_semantic is rule.geometry_semantic
        and fact.metric_key == rule.metric_key
    )
    if not matching:
        return (
            RuleEvaluation(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                entity_id=None,
                status=VastuStatus.NOT_APPLICABLE,
                actual_value=None,
                raw_weight=rule.weight,
                earned_weight=0,
            ),
        )

    results: list[RuleEvaluation] = []
    for fact in sorted(matching, key=lambda item: item.entity_id):
        passed = _predicate_passes(rule, fact)
        results.append(
            RuleEvaluation(
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                entity_id=fact.entity_id,
                status=VastuStatus.PASS if passed else VastuStatus.FAIL,
                actual_value=fact.value,
                raw_weight=rule.weight,
                earned_weight=rule.weight if passed else 0,
                evidence=fact.evidence,
            )
        )
    return tuple(results)


def evaluate_bundle(
    bundle: RuleBundle,
    facts: Iterable[VastuFact],
) -> tuple[RuleEvaluation, ...]:
    fact_tuple = tuple(facts)
    evaluations: list[RuleEvaluation] = []
    for rule in bundle.rules:
        evaluations.extend(evaluate_rule(rule, fact_tuple))
    return tuple(evaluations)
