from pathlib import Path

from ai_vastu.vastu import RuleLifecycle
from ai_vastu.vastu_spec import ReviewStatus, SpecLifecycle, load_vastu_spec_directory

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"

spec = load_vastu_spec_directory(SPEC_ROOT)

if spec.manifest.lifecycle is not SpecLifecycle.FROZEN:
    raise SystemExit(
        "Phase 20B expects Vastu Specification v1.0 to be FROZEN after explicit human approval."
    )
if len(spec.rule_records) != 4:
    raise SystemExit(
        f"Phase 20B expects exactly four production rules, got {len(spec.rule_records)}."
    )
if spec.manifest.production_rule_count != 4:
    raise SystemExit("Phase 20B production_rule_count must be exactly four.")
if spec.manifest.expected_rule_bundle_hash is None:
    raise SystemExit("Phase 20B requires a pinned production rule-bundle hash.")
if not spec.production_ready:
    raise SystemExit("Frozen Vastu specification did not report production_ready=true.")

for record in spec.rule_records:
    if record.rule.lifecycle is not RuleLifecycle.FROZEN:
        raise SystemExit(f"Rule {record.rule.rule_id} is not FROZEN.")
    if record.review.status is not ReviewStatus.APPROVED:
        raise SystemExit(f"Rule {record.rule.rule_id} is not APPROVED.")

print(
    "Vastu Specification v1.0 production files are valid: "
    f"lifecycle={spec.manifest.lifecycle.value}, rules={len(spec.rule_records)}, "
    f"bundle_hash={spec.manifest.expected_rule_bundle_hash}, "
    f"authoring_hash={spec.authoring_content_hash}"
)
