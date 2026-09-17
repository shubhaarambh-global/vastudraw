from __future__ import annotations

import json
from pathlib import Path

from ai_vastu.release import ReleaseDisposition, evaluate_production_mvp_readiness
from ai_vastu.vastu import SourceRegistry, compile_rule_bundle
from ai_vastu.vastu_spec import (
    ReviewDecision,
    ReviewerRole,
    compile_production_release,
    load_vastu_spec_directory,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"
PRODUCTION_ROOT = SPEC_ROOT / "production"

spec = load_vastu_spec_directory(SPEC_ROOT)
registry = SourceRegistry(spec.sources)
bundle = compile_rule_bundle(
    spec_version=spec.manifest.spec_version,
    rules=(record.rule for record in spec.rule_records),
    source_registry=registry,
    production=True,
)

if bundle.content_hash != spec.manifest.expected_rule_bundle_hash:
    raise SystemExit("Compiled bundle hash does not match frozen manifest.")

stored_bundle = json.loads((PRODUCTION_ROOT / "rule-bundle.json").read_text(encoding="utf-8"))
if stored_bundle != bundle.model_dump(mode="json"):
    raise SystemExit("Stored production rule bundle does not match deterministic compilation.")

approval_times = [
    item.reviewed_at
    for record in spec.rule_records
    for item in record.review.attestations
    if item.role is ReviewerRole.VASTU_EXPERT and item.decision is ReviewDecision.APPROVE
]
if not approval_times:
    raise SystemExit("No VASTU_EXPERT approval timestamp exists.")
release = compile_production_release(spec, released_at=max(approval_times))
stored_release = json.loads((PRODUCTION_ROOT / "release.json").read_text(encoding="utf-8"))
if stored_release != release.model_dump(mode="json"):
    raise SystemExit("Stored production release does not match deterministic compilation.")

report = evaluate_production_mvp_readiness(ROOT)
if report.disposition is not ReleaseDisposition.READY:
    raise SystemExit("Phase 20B expected production MVP readiness to be READY.")
if report.blocker_codes != () or report.blocker_count != 0:
    raise SystemExit("Phase 20B expected zero production MVP blockers.")

print(
    "Vastu production release deterministic: "
    f"rules={len(bundle.rules)}, bundle_hash={bundle.content_hash}, "
    f"release_hash={release.release_hash}, mvp_status={report.disposition.value}, blockers=0"
)
