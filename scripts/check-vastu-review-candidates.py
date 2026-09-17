from __future__ import annotations

import json
from pathlib import Path

from ai_vastu.vastu import (
    RuleClassification,
    RuleLifecycle,
    SourceRegistry,
)
from ai_vastu.vastu_spec import (
    ReviewDecision,
    ReviewerRole,
    ReviewStatus,
    SpecLifecycle,
    build_review_packet,
    load_vastu_spec_directory,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"
PACKET_ROOT = SPEC_ROOT / "review-packets"

EXPECTED_RULE_IDS = (
    "VASTU-BATH-EAST-001",
    "VASTU-KITCHEN-SE-001",
    "VASTU-MASTER-BEDROOM-SOUTH-001",
    "VASTU-PUJA-NE-001",
)

spec = load_vastu_spec_directory(SPEC_ROOT)

assert spec.manifest.lifecycle is SpecLifecycle.FROZEN
assert spec.manifest.rule_ids == EXPECTED_RULE_IDS
assert spec.manifest.production_rule_count == 4
assert spec.manifest.expected_rule_bundle_hash is not None
assert spec.production_ready

registry = SourceRegistry(spec.sources)
expert_reviewer_ids: set[str] = set()

for record in spec.rule_records:
    assert record.rule.lifecycle is RuleLifecycle.FROZEN
    assert record.rule.classification is RuleClassification.SOFT
    assert record.review.status is ReviewStatus.APPROVED
    assert record.review.source_validation_passed is True
    assert record.review.geometry_semantics_reviewed is True

    expert_approvals = tuple(
        item
        for item in record.review.attestations
        if item.role is ReviewerRole.VASTU_EXPERT and item.decision is ReviewDecision.APPROVE
    )
    assert expert_approvals
    expert_reviewer_ids.update(item.reviewer_id for item in expert_approvals)

    for reference in record.rule.source_refs:
        registry.require(reference)

    expected_packet = build_review_packet(record, source_registry=registry)
    packet_path = PACKET_ROOT / f"{record.rule.rule_id}.json"
    actual_packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert actual_packet == expected_packet

print(
    "Phase 20B Vastu review approved: "
    f"rules={len(spec.rule_records)}, expert_reviewers={len(expert_reviewer_ids)}, "
    "geometry_reviewed=true, production_frozen=true, "
    f"authoring_hash={spec.authoring_content_hash}"
)
