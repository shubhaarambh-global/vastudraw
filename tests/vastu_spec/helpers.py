from __future__ import annotations

from datetime import UTC, datetime

from ai_vastu.vastu import (
    GeometrySemantic,
    NumericRangePredicate,
    RuleClassification,
    RuleLifecycle,
    RuleSeverity,
    SourceRecord,
    SourceReference,
    SubjectSelector,
    VastuRule,
)
from ai_vastu.vastu_spec import (
    ReviewDecision,
    ReviewerAttestation,
    ReviewerRole,
    ReviewStatus,
    RuleAuthoringRecord,
    RuleReview,
)


def synthetic_source() -> SourceRecord:
    return SourceRecord(
        source_id="SYNTHETIC-SOURCE-001",
        title="Synthetic source for specification workflow tests",
        author_or_institution="AI Vastu Architect test suite",
        notes="Not a Vastu authority and never loaded by the repository production spec.",
    )


def approved_synthetic_record(*, rule_id: str = "SYNTHETIC-RULE-001") -> RuleAuthoringRecord:
    rule = VastuRule(
        rule_id=rule_id,
        rule_version="1.0.0",
        spec_version="1.0.0",
        lifecycle=RuleLifecycle.FROZEN,
        category="SYNTHETIC_TEST",
        subject=SubjectSelector(entity_type="synthetic_space"),
        geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
        predicate=NumericRangePredicate(
            metric_key="synthetic_overlap_bp",
            minimum_inclusive=8_000,
            maximum_inclusive=10_000,
        ),
        classification=RuleClassification.SOFT,
        severity=RuleSeverity.MAJOR,
        weight=100,
        precedence=100,
        source_refs=(
            SourceReference(
                source_id="SYNTHETIC-SOURCE-001",
                locator="test-fixture",
                interpretation_note="Synthetic only.",
            ),
        ),
        explanation_template="Synthetic explanation from measured evidence.",
    )
    review = RuleReview(
        status=ReviewStatus.APPROVED,
        source_validation_passed=True,
        geometry_semantics_reviewed=True,
        attestations=(
            ReviewerAttestation(
                reviewer_id="SYNTHETIC-REVIEWER-001",
                role=ReviewerRole.VASTU_EXPERT,
                decision=ReviewDecision.APPROVE,
                reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
                note="Synthetic approval used only to test the workflow.",
            ),
        ),
    )
    return RuleAuthoringRecord(
        rule=rule,
        normalized_statement="Synthetic rule statement for workflow testing.",
        interpretation_notes="No Vastu doctrine claim; deterministic test fixture only.",
        review=review,
    )
