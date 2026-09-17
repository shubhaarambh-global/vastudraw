from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ai_vastu.vastu import (
    RuleLifecycle,
    SourceRegistry,
    compile_rule_bundle,
)
from ai_vastu.vastu_spec import (
    LoadedVastuSpecification,
    ReviewDecision,
    ReviewerRole,
    ReviewStatus,
    SpecLifecycle,
    VastuSpecManifest,
    build_review_packet,
    compile_production_release,
    load_vastu_spec_directory,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"
MANIFEST_PATH = SPEC_ROOT / "manifest.json"
PACKET_ROOT = SPEC_ROOT / "review-packets"
PRODUCTION_ROOT = SPEC_ROOT / "production"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _expert_approval_times(spec: LoadedVastuSpecification) -> list[datetime]:
    # Kept as a small helper to make the release timestamp derivation auditable.
    result: list[datetime] = []
    for record in spec.rule_records:
        for item in record.review.attestations:
            if item.role is ReviewerRole.VASTU_EXPERT and item.decision is ReviewDecision.APPROVE:
                result.append(item.reviewed_at)
    return result


def main() -> None:
    spec = load_vastu_spec_directory(SPEC_ROOT)
    if len(spec.rule_records) != 4:
        raise SystemExit(f"Phase 20B expects exactly four rules, got {len(spec.rule_records)}.")

    for record in spec.rule_records:
        if record.rule.lifecycle is not RuleLifecycle.FROZEN:
            raise SystemExit(f"Rule {record.rule.rule_id} is not FROZEN.")
        if record.review.status is not ReviewStatus.APPROVED:
            raise SystemExit(f"Rule {record.rule.rule_id} is not APPROVED.")
        if not record.review.source_validation_passed:
            raise SystemExit(f"Rule {record.rule.rule_id} lacks source validation.")
        if not record.review.geometry_semantics_reviewed:
            raise SystemExit(f"Rule {record.rule.rule_id} lacks geometry-semantics review.")
        if not any(
            item.role is ReviewerRole.VASTU_EXPERT and item.decision is ReviewDecision.APPROVE
            for item in record.review.attestations
        ):
            raise SystemExit(f"Rule {record.rule.rule_id} lacks VASTU_EXPERT approval.")

    registry = SourceRegistry(spec.sources)
    bundle = compile_rule_bundle(
        spec_version=spec.manifest.spec_version,
        rules=(record.rule for record in spec.rule_records),
        source_registry=registry,
        production=True,
    )

    manifest = VastuSpecManifest(
        spec_version="1.0.0",
        title=spec.manifest.title,
        lifecycle=SpecLifecycle.FROZEN,
        rule_ids=spec.manifest.rule_ids,
        production_rule_count=len(spec.rule_records),
        expected_rule_bundle_hash=bundle.content_hash,
        notes=(
            "Phase 20B production freeze. Four source-verified SOFT rules carry "
            "explicit human VASTU_EXPERT approval and reviewed geometry semantics."
        ),
    )
    _write_json(MANIFEST_PATH, manifest.model_dump(mode="json"))

    frozen_spec = load_vastu_spec_directory(SPEC_ROOT)
    approval_times = _expert_approval_times(frozen_spec)
    if not approval_times:
        raise SystemExit("No VASTU_EXPERT approval timestamp is available for release.")
    released_at = max(approval_times)

    release = compile_production_release(frozen_spec, released_at=released_at)

    _write_json(
        PRODUCTION_ROOT / "rule-bundle.json",
        bundle.model_dump(mode="json"),
    )
    _write_json(
        PRODUCTION_ROOT / "release.json",
        release.model_dump(mode="json"),
    )

    PACKET_ROOT.mkdir(parents=True, exist_ok=True)
    expected_packet_paths: set[Path] = set()
    for record in frozen_spec.rule_records:
        packet = build_review_packet(record, source_registry=registry)
        packet_path = PACKET_ROOT / f"{record.rule.rule_id}.json"
        expected_packet_paths.add(packet_path)
        _write_json(packet_path, packet)
    for stale in PACKET_ROOT.glob("*.json"):
        if stale not in expected_packet_paths:
            stale.unlink()

    expert_ids = sorted(
        {
            item.reviewer_id
            for record in frozen_spec.rule_records
            for item in record.review.attestations
            if item.role is ReviewerRole.VASTU_EXPERT and item.decision is ReviewDecision.APPROVE
        }
    )
    (SPEC_ROOT / "README.md").write_text(
        "# Vastu Specification v1.0 — production-frozen state\n\n"
        "Phase 20B records explicit human `VASTU_EXPERT` approval for the four "
        "source-backed residential room-placement rules and freezes the production bundle.\n\n"
        f"- lifecycle: `FROZEN`\n"
        f"- production rules: `{len(frozen_spec.rule_records)}`\n"
        f"- RuleBundle SHA-256: `{bundle.content_hash}`\n"
        f"- reviewer IDs: `{', '.join(expert_ids)}`\n\n"
        "All four rules remain `SOFT`; they do not override structural, fire/life-safety, "
        "accessibility, sanitation, planning/bylaw, climate, daylight/ventilation, or other "
        "statutory requirements.\n",
        encoding="utf-8",
    )
    (SPEC_ROOT / "review-summary.md").write_text(
        "# Phase 20B — approved Vastu v1.0 review summary\n\n"
        "The human VASTU_EXPERT reviewer approved the four Phase 20A normalized statements "
        "and the current v1.0 geometry/scoring semantics.\n\n"
        "| Rule | Frozen production interpretation | Review |\n"
        "| --- | --- | --- |\n"
        "| VASTU-PUJA-NE-001 | Puja/meditation: NE; 8-sector centroid "
        "classification. | APPROVED |\n"
        "| VASTU-KITCHEN-SE-001 | Kitchen: SE primary only; no inferred NW fallback. | APPROVED |\n"
        "| VASTU-MASTER-BEDROOM-SOUTH-001 | `master_bedroom`: S or SW. | APPROVED |\n"
        "| VASTU-BATH-EAST-001 | Dedicated `bath`: E; toilet rules remain "
        "separate. | APPROVED |\n\n"
        f"Production RuleBundle SHA-256: `{bundle.content_hash}`\n\n"
        f"Reviewer IDs: `{', '.join(expert_ids)}`\n",
        encoding="utf-8",
    )
    (PACKET_ROOT / "README.md").write_text(
        "# Phase 20B approved review packets\n\n"
        "Run `pnpm vastu:packets` to regenerate deterministic JSON evidence packets. "
        "The JSON packets mirror the final approved rule records and human attestation.\n",
        encoding="utf-8",
    )

    print(
        "Vastu Specification v1.0 frozen: "
        f"rules={len(bundle.rules)}, bundle_hash={bundle.content_hash}, "
        f"release_hash={release.release_hash}, released_at={release.released_at.isoformat()}"
    )


if __name__ == "__main__":
    main()
