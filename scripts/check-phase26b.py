from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]

required = (
    root / "python/ai_vastu/vastu_reasoning/models.py",
    root / "python/ai_vastu/vastu_reasoning/service.py",
    root / "python/ai_vastu/vastu_reasoning/evaluator.py",
    root / "python/ai_vastu/vastu_reasoning/scoring.py",
    root / "docs/vastu/spec-v2-draft/seed-rule-catalog.json",
    root / "tests/test_phase26b_policy.py",
)
missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Phase 26B missing files: " + ", ".join(missing))

catalog = json.loads(
    (root / "docs/vastu/spec-v2-draft/seed-rule-catalog.json").read_text(encoding="utf-8")
)
if catalog.get("hard_constraints_allowed") is not False:
    raise SystemExit("Phase 26B policy failure: hard Vastu constraints enabled.")
if any(rule.get("hard_constraint") is not False for rule in catalog["rules"]):
    raise SystemExit("Phase 26B policy failure: a soft Vastu rule became hard.")

orchestrator = (root / "python/ai_vastu/requirements/final_orchestrator.py").read_text(
    encoding="utf-8"
)
route = (root / "apps/api/app/confirmed_generation_routes.py").read_text(encoding="utf-8")
finalization = (root / "python/ai_vastu/requirements/finalization.py").read_text(encoding="utf-8")

checks = {
    "reasoning-enabled": "vastu_reasoning_enabled()" in orchestrator,
    "provider-service": "create_vastu_reasoning_service()" in orchestrator,
    "assessment-after-canonical": "assess_plan(" in orchestrator,
    "planning-blend": "blend_plan_scores(" in orchestrator,
    "api-profile-both-branches": route.count('"vastu_reasoning_profile"') == 2,
    "api-assessment-both-branches": route.count('"vastu_assessment"') == 2,
    "api-blend-both-branches": route.count('"planning_blend"') == 2,
    "frozen-v1-hash-preserved": (
        "b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667" in finalization
    ),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Phase 26B integration checks failed: " + ", ".join(failed))

print("Phase 26B soft Vastu reasoning integration: OK")
print("Catalog rules:", len(catalog["rules"]))
print("Hard Vastu constraints: disabled")
print("Frozen Vastu v1 bundle: preserved")
