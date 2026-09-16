from __future__ import annotations

import pytest

from ai_vastu.vastu import (
    RuleClassification,
    RuleConflictError,
    RuleLifecycle,
    RuleSourceError,
    SourceRecord,
    SourceRegistry,
    compile_rule_bundle,
)

from .helpers import numeric_rule, source


def test_source_registry_rejects_duplicate_ids() -> None:
    with pytest.raises(RuleSourceError, match="Duplicate"):
        SourceRegistry((source(), source()))


def test_production_bundle_contains_only_frozen_rules() -> None:
    registry = SourceRegistry((source(),))
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=registry,
        rules=(
            numeric_rule(rule_id="SYNTHETIC-RULE-001", lifecycle=RuleLifecycle.FROZEN),
            numeric_rule(rule_id="SYNTHETIC-RULE-002", lifecycle=RuleLifecycle.REVIEWED),
            numeric_rule(rule_id="SYNTHETIC-RULE-003", lifecycle=RuleLifecycle.DRAFT),
            numeric_rule(rule_id="SYNTHETIC-RULE-004", lifecycle=RuleLifecycle.RETIRED),
        ),
    )
    assert [rule.rule_id for rule in bundle.rules] == ["SYNTHETIC-RULE-001"]
    assert bundle.verify_hash()


def test_bundle_hash_is_deterministic_across_input_order() -> None:
    registry = SourceRegistry((source(),))
    first_rule = numeric_rule(rule_id="SYNTHETIC-RULE-001")
    second_rule = numeric_rule(rule_id="SYNTHETIC-RULE-002", minimum=5_000)
    first = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=registry,
        rules=(first_rule, second_rule),
    )
    second = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=registry,
        rules=(second_rule, first_rule),
    )
    assert first.content_hash == second.content_hash
    assert first.rules == second.rules


def test_unknown_source_fails_closed() -> None:
    with pytest.raises(RuleSourceError, match="unknown source"):
        compile_rule_bundle(
            spec_version="1.0.0",
            source_registry=SourceRegistry(()),
            rules=(numeric_rule(),),
        )


def test_contradictory_equal_precedence_hard_ranges_are_rejected() -> None:
    registry = SourceRegistry((source(),))
    with pytest.raises(RuleConflictError, match="Contradictory"):
        compile_rule_bundle(
            spec_version="1.0.0",
            source_registry=registry,
            rules=(
                numeric_rule(
                    rule_id="SYNTHETIC-HARD-001",
                    classification=RuleClassification.HARD,
                    minimum=8_000,
                    maximum=10_000,
                ),
                numeric_rule(
                    rule_id="SYNTHETIC-HARD-002",
                    classification=RuleClassification.HARD,
                    minimum=0,
                    maximum=4_000,
                ),
            ),
        )


def test_compatible_hard_ranges_can_coexist() -> None:
    registry = SourceRegistry((source(),))
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=registry,
        rules=(
            numeric_rule(
                rule_id="SYNTHETIC-HARD-001",
                classification=RuleClassification.HARD,
                minimum=5_000,
                maximum=10_000,
            ),
            numeric_rule(
                rule_id="SYNTHETIC-HARD-002",
                classification=RuleClassification.HARD,
                minimum=8_000,
                maximum=10_000,
            ),
        ),
    )
    assert len(bundle.rules) == 2


def test_rule_spec_version_mismatch_fails_closed() -> None:
    registry = SourceRegistry((source(),))
    payload = numeric_rule().model_dump()
    payload["spec_version"] = "2.0.0"
    from ai_vastu.vastu import VastuRule

    with pytest.raises(RuleConflictError, match="belongs to spec"):
        compile_rule_bundle(
            spec_version="1.0.0",
            source_registry=registry,
            rules=(VastuRule.model_validate(payload),),
        )


def test_only_referenced_sources_enter_bundle() -> None:
    extra = SourceRecord(source_id="SYNTHETIC-SOURCE-999", title="Unused synthetic source")
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=SourceRegistry((source(), extra)),
        rules=(numeric_rule(),),
    )
    assert [item.source_id for item in bundle.sources] == ["SYNTHETIC-SOURCE-001"]
