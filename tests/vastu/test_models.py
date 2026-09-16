from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_vastu.vastu import (
    BooleanPredicate,
    GeometrySemantic,
    RuleClassification,
    RuleLifecycle,
    RuleSeverity,
    SubjectSelector,
    VastuRule,
)

from .helpers import numeric_rule


def test_frozen_rule_requires_provenance() -> None:
    with pytest.raises(ValidationError, match="source reference"):
        VastuRule(
            rule_id="SYNTHETIC-RULE-999",
            rule_version="1.0.0",
            spec_version="1.0.0",
            lifecycle=RuleLifecycle.FROZEN,
            category="SYNTHETIC_TEST",
            subject=SubjectSelector(entity_type="synthetic_space"),
            geometry_semantic=GeometrySemantic.POINT_IN_ZONE,
            predicate=BooleanPredicate(metric_key="synthetic_point_in_zone", expected=True),
            classification=RuleClassification.HARD,
            severity=RuleSeverity.MAJOR,
            weight=100,
            explanation_template="Synthetic only.",
        )


def test_draft_rule_may_exist_before_source_review() -> None:
    rule = numeric_rule(lifecycle=RuleLifecycle.DRAFT)
    assert rule.source_refs == ()


def test_versions_are_explicit_semver() -> None:
    base = numeric_rule().model_dump()
    base["rule_version"] = "v1"
    with pytest.raises(ValidationError, match=r"MAJOR\.MINOR\.PATCH"):
        VastuRule.model_validate(base)


def test_rule_models_are_immutable() -> None:
    rule = numeric_rule()
    with pytest.raises(ValidationError):
        rule.weight = 12  # type: ignore[misc]
