from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_vastu.vastu import RuleLifecycle
from ai_vastu.vastu_spec import (
    ReviewDecision,
    ReviewerAttestation,
    ReviewerRole,
    ReviewStatus,
    RuleAuthoringRecord,
    RuleReview,
    SpecLifecycle,
    VastuSpecManifest,
)

from .helpers import approved_synthetic_record


def test_approved_review_requires_vastu_expert_approval() -> None:
    with pytest.raises(ValidationError, match="VASTU_EXPERT"):
        RuleReview(
            status=ReviewStatus.APPROVED,
            source_validation_passed=True,
            geometry_semantics_reviewed=True,
            attestations=(
                ReviewerAttestation(
                    reviewer_id="SYNTHETIC-TECH-001",
                    role=ReviewerRole.TECHNICAL_REVIEWER,
                    decision=ReviewDecision.APPROVE,
                    reviewed_at=datetime(2026, 1, 1, tzinfo=UTC),
                    note="Synthetic technical approval.",
                ),
            ),
        )


def test_frozen_rule_cannot_have_draft_review() -> None:
    approved = approved_synthetic_record()
    payload = approved.model_dump()
    payload["review"] = RuleReview(status=ReviewStatus.DRAFT).model_dump()
    with pytest.raises(ValidationError, match="APPROVED"):
        RuleAuthoringRecord.model_validate(payload)


def test_approved_record_cannot_leave_rule_unfrozen() -> None:
    approved = approved_synthetic_record()
    payload = approved.model_dump()
    payload["rule"]["lifecycle"] = RuleLifecycle.REVIEWED
    with pytest.raises(ValidationError, match="FROZEN"):
        RuleAuthoringRecord.model_validate(payload)


def test_reviewer_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ReviewerAttestation(
            reviewer_id="SYNTHETIC-REVIEWER-001",
            role=ReviewerRole.VASTU_EXPERT,
            decision=ReviewDecision.APPROVE,
            reviewed_at=datetime(2026, 1, 1),
            note="Synthetic only.",
        )


def test_frozen_manifest_cannot_be_empty() -> None:
    with pytest.raises(ValidationError, match="zero rules"):
        VastuSpecManifest(
            spec_version="1.0.0",
            title="Synthetic",
            lifecycle=SpecLifecycle.FROZEN,
            rule_ids=(),
            production_rule_count=0,
            expected_rule_bundle_hash="0" * 64,
        )
