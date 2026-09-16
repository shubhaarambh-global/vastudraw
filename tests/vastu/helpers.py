from __future__ import annotations

from ai_vastu.vastu import (
    GeometrySemantic,
    NumericRangePredicate,
    RuleClassification,
    RuleLifecycle,
    RuleSeverity,
    SourceRecord,
    SourceReference,
    SubjectAttribute,
    SubjectSelector,
    VastuRule,
)


def source() -> SourceRecord:
    return SourceRecord(
        source_id="SYNTHETIC-SOURCE-001",
        title="Synthetic test source — not a production Vastu authority",
        author_or_institution="AI Vastu Architect test suite",
        notes="Used only to validate rule infrastructure.",
    )


def numeric_rule(
    *,
    rule_id: str = "SYNTHETIC-RULE-001",
    lifecycle: RuleLifecycle = RuleLifecycle.FROZEN,
    classification: RuleClassification = RuleClassification.SOFT,
    minimum: int | None = 8_000,
    maximum: int | None = 10_000,
    precedence: int = 100,
    attributes: tuple[SubjectAttribute, ...] = (),
) -> VastuRule:
    refs = (
        SourceReference(
            source_id="SYNTHETIC-SOURCE-001",
            locator="test-fixture",
            interpretation_note="Synthetic rule; no Vastu content claim.",
        ),
    )
    return VastuRule(
        rule_id=rule_id,
        rule_version="1.0.0",
        spec_version="1.0.0",
        lifecycle=lifecycle,
        category="SYNTHETIC_TEST",
        subject=SubjectSelector(entity_type="synthetic_space", attributes=attributes),
        geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
        predicate=NumericRangePredicate(
            metric_key="synthetic_zone_overlap_bp",
            minimum_inclusive=minimum,
            maximum_inclusive=maximum,
        ),
        classification=classification,
        severity=RuleSeverity.MAJOR,
        weight=100,
        precedence=precedence,
        source_refs=refs if lifecycle in {RuleLifecycle.REVIEWED, RuleLifecycle.FROZEN} else (),
        explanation_template="Synthetic explanation based on measured evidence.",
    )
