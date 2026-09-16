from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .errors import RuleBundleIntegrityError, RuleConflictError
from .models import (
    BooleanPredicate,
    EnumSetPredicate,
    NumericRangePredicate,
    RuleBundle,
    RuleClassification,
    RuleLifecycle,
    VastuRule,
)
from .source_registry import SourceRegistry


def _predicates_are_compatible(
    first: NumericRangePredicate | EnumSetPredicate | BooleanPredicate,
    second: NumericRangePredicate | EnumSetPredicate | BooleanPredicate,
) -> bool:
    if first.kind is not second.kind:
        return False

    if isinstance(first, NumericRangePredicate) and isinstance(second, NumericRangePredicate):
        first_min = first.minimum_inclusive
        second_min = second.minimum_inclusive
        first_max = first.maximum_inclusive
        second_max = second.maximum_inclusive
        lower_candidates = [value for value in (first_min, second_min) if value is not None]
        upper_candidates = [value for value in (first_max, second_max) if value is not None]
        lower = max(lower_candidates) if lower_candidates else None
        upper = min(upper_candidates) if upper_candidates else None
        return lower is None or upper is None or lower <= upper

    if isinstance(first, EnumSetPredicate) and isinstance(second, EnumSetPredicate):
        return bool(set(first.allowed_values) & set(second.allowed_values))

    if isinstance(first, BooleanPredicate) and isinstance(second, BooleanPredicate):
        return first.expected is second.expected

    return False


def _reject_hard_conflicts(rules: Iterable[VastuRule]) -> None:
    grouped: dict[tuple[object, ...], list[VastuRule]] = defaultdict(list)
    for rule in rules:
        if rule.classification is RuleClassification.HARD:
            grouped[rule.conflict_key()].append(rule)

    for key, candidates in grouped.items():
        for index, first in enumerate(candidates):
            for second in candidates[index + 1 :]:
                if not _predicates_are_compatible(first.predicate, second.predicate):
                    raise RuleConflictError(
                        "Contradictory hard Vastu rules at equal precedence: "
                        f"{first.rule_id} vs {second.rule_id}; key={key!r}."
                    )


def compile_rule_bundle(
    *,
    spec_version: str,
    rules: Iterable[VastuRule],
    source_registry: SourceRegistry,
    production: bool = True,
) -> RuleBundle:
    candidates = tuple(rules)
    rule_ids = [rule.rule_id for rule in candidates]
    if len(rule_ids) != len(set(rule_ids)):
        raise RuleConflictError("A rule bundle cannot contain duplicate rule_id values.")

    for rule in candidates:
        if rule.spec_version != spec_version:
            raise RuleConflictError(
                f"Rule {rule.rule_id} belongs to spec {rule.spec_version}, expected {spec_version}."
            )
        source_registry.validate_references(rule.source_refs)

    if production:
        selected = tuple(rule for rule in candidates if rule.lifecycle is RuleLifecycle.FROZEN)
    else:
        selected = tuple(rule for rule in candidates if rule.lifecycle is not RuleLifecycle.RETIRED)

    selected = tuple(sorted(selected, key=lambda rule: (rule.rule_id, rule.rule_version)))
    _reject_hard_conflicts(selected)

    referenced_source_ids = {
        reference.source_id for rule in selected for reference in rule.source_refs
    }
    sources = tuple(
        record for record in source_registry.records if record.source_id in referenced_source_ids
    )

    provisional = RuleBundle(
        spec_version=spec_version,
        production=production,
        rules=selected,
        sources=sources,
        content_hash="0" * 64,
    )
    bundle = provisional.model_copy(update={"content_hash": provisional.compute_content_hash()})
    if not bundle.verify_hash():
        raise RuleBundleIntegrityError("Compiled rule bundle hash did not verify.")
    return bundle
