from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ai_vastu.vastu import RuleLifecycle
from ai_vastu.vastu_spec import (
    ReviewDecision,
    ReviewerAttestation,
    ReviewerRole,
    ReviewStatus,
    RuleAuthoringRecord,
    RuleReview,
    SpecLifecycle,
    load_vastu_spec_directory,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"
RULE_ROOT = SPEC_ROOT / "rules"
CONFIRMATION_TOKEN = "I_APPROVE_PHASE20B_V1"
APPROVAL_NOTE = (
    "I reviewed the Phase 20A Vastu v1.0 review summary and approve all four "
    "normalized source-backed statements for the MVP; the current eight-sector "
    "direction model and CENTROID_IN_ZONE geometry semantics; SE-only primary "
    "kitchen placement without an inferred NW fallback; the master_bedroom-only "
    "S/SW predicate; separate bath and toilet treatment; and the current SOFT "
    "weights/severities."
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record an explicit human VASTU_EXPERT approval for Phase 20B."
    )
    parser.add_argument(
        "--reviewer-id",
        required=True,
        help="Stable project-local reviewer identifier using uppercase ID syntax.",
    )
    parser.add_argument(
        "--confirmation",
        required=True,
        help=f"Must equal {CONFIRMATION_TOKEN!r}.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.confirmation != CONFIRMATION_TOKEN:
        raise SystemExit(
            "Approval not recorded: explicit confirmation token did not match."
        )

    spec = load_vastu_spec_directory(SPEC_ROOT)
    if spec.manifest.lifecycle not in {SpecLifecycle.IN_REVIEW, SpecLifecycle.FROZEN}:
        raise SystemExit(
            f"Approval requires IN_REVIEW/FROZEN spec state, got {spec.manifest.lifecycle.value}."
        )
    if len(spec.rule_records) != 4:
        raise SystemExit(f"Phase 20B expects exactly four rules, got {len(spec.rule_records)}.")

    reviewed_at = datetime.now().astimezone()
    updated = 0
    already_approved = 0

    for record in spec.rule_records:
        existing = tuple(
            item
            for item in record.review.attestations
            if item.reviewer_id == args.reviewer_id
            and item.role is ReviewerRole.VASTU_EXPERT
            and item.decision is ReviewDecision.APPROVE
        )

        if existing:
            if (
                record.review.status is not ReviewStatus.APPROVED
                or not record.review.geometry_semantics_reviewed
                or record.rule.lifecycle is not RuleLifecycle.FROZEN
            ):
                raise SystemExit(
                    f"Rule {record.rule.rule_id} contains a partial existing approval state."
                )
            already_approved += 1
            continue

        if record.review.status not in {
            ReviewStatus.SOURCE_VERIFIED,
            ReviewStatus.DOMAIN_REVIEWED,
        }:
            raise SystemExit(
                f"Rule {record.rule.rule_id} is not eligible for approval from state "
                f"{record.review.status.value}."
            )
        if not record.review.source_validation_passed:
            raise SystemExit(
                f"Rule {record.rule.rule_id} has not passed source validation."
            )
        if any(
            item.decision is ReviewDecision.REJECT
            for item in record.review.attestations
        ):
            raise SystemExit(
                f"Rule {record.rule.rule_id} contains a rejection attestation."
            )

        attestation = ReviewerAttestation(
            reviewer_id=args.reviewer_id,
            role=ReviewerRole.VASTU_EXPERT,
            decision=ReviewDecision.APPROVE,
            reviewed_at=reviewed_at,
            note=APPROVAL_NOTE,
        )
        approved_review = RuleReview(
            status=ReviewStatus.APPROVED,
            source_validation_passed=True,
            geometry_semantics_reviewed=True,
            attestations=(*record.review.attestations, attestation),
        )
        frozen_rule = record.rule.model_copy(update={"lifecycle": RuleLifecycle.FROZEN})
        approved_record = RuleAuthoringRecord(
            rule=frozen_rule,
            normalized_statement=record.normalized_statement,
            interpretation_notes=record.interpretation_notes,
            review=approved_review,
        )

        path = RULE_ROOT / f"{record.rule.rule_id}.json"
        path.write_text(
            json.dumps(
                approved_record.model_dump(mode="json"),
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )
        updated += 1

    print(
        "Human VASTU_EXPERT approval recorded: "
        f"reviewer_id={args.reviewer_id}, updated={updated}, "
        f"already_approved={already_approved}, confirmation={CONFIRMATION_TOKEN}"
    )
    print("Approved semantics:")
    print(APPROVAL_NOTE)


if __name__ == "__main__":
    main()
