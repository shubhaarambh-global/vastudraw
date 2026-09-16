from pathlib import Path

from ai_vastu.release import ReleaseDisposition, evaluate_production_mvp_readiness
from ai_vastu.vastu import RuleClassification, RuleLifecycle
from ai_vastu.vastu_spec import (
    ReviewDecision,
    ReviewerRole,
    ReviewStatus,
    SpecLifecycle,
    load_vastu_spec_directory,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"


def test_phase20b_rules_are_human_approved_and_frozen() -> None:
    spec = load_vastu_spec_directory(SPEC_ROOT)

    assert spec.manifest.lifecycle is SpecLifecycle.FROZEN
    assert spec.manifest.production_rule_count == 4
    assert spec.manifest.expected_rule_bundle_hash is not None
    assert len(spec.rule_records) == 4

    for record in spec.rule_records:
        assert record.rule.lifecycle is RuleLifecycle.FROZEN
        assert record.rule.classification is RuleClassification.SOFT
        assert record.review.status is ReviewStatus.APPROVED
        assert record.review.source_validation_passed is True
        assert record.review.geometry_semantics_reviewed is True
        assert any(
            item.role is ReviewerRole.VASTU_EXPERT
            and item.decision is ReviewDecision.APPROVE
            for item in record.review.attestations
        )


def test_phase20b_approval_requires_explicit_human_confirmation_token() -> None:
    source = (ROOT / "scripts/record-vastu-expert-approval.py").read_text(
        encoding="utf-8"
    )
    assert 'CONFIRMATION_TOKEN = "I_APPROVE_PHASE20B_V1"' in source
    assert "ReviewerRole.VASTU_EXPERT" in source
    assert "datetime.now().astimezone()" in source


def test_phase20b_release_gate_is_ready_with_zero_blockers() -> None:
    report = evaluate_production_mvp_readiness(ROOT)
    assert report.disposition is ReleaseDisposition.READY
    assert report.blocker_codes == ()
    assert report.blocker_count == 0


def test_phase20b_scripts_are_wired_into_validation() -> None:
    package = (ROOT / "package.json").read_text(encoding="utf-8")
    assert '"vastu:approve"' in package
    assert '"vastu:freeze"' in package
    assert '"vastu:production"' in package
    assert "pnpm vastu:check && pnpm vastu:review && pnpm vastu:production &&" in package
