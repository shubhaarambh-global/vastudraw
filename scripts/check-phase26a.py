from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1]

required = (
    root / "python/ai_vastu/architectural_intelligence/models.py",
    root / "python/ai_vastu/architectural_intelligence/compiler.py",
    root / "python/ai_vastu/architectural_intelligence/service.py",
    root / "python/ai_vastu/architectural_intelligence/providers/gemini.py",
    root / "python/ai_vastu/architectural_intelligence/providers/openai_responses.py",
    root / "tests/test_phase26a_policy.py",
)

missing = [str(path.relative_to(root)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Phase 26A missing files: " + ", ".join(missing))

orchestrator = (root / "python/ai_vastu/requirements/final_orchestrator.py").read_text(
    encoding="utf-8"
)
route = (root / "apps/api/app/confirmed_generation_routes.py").read_text(encoding="utf-8")

checks = {
    "orchestrator-enabled-gate": "architectural_intelligence_enabled()" in orchestrator,
    "orchestrator-reasoning": "create_architectural_intelligence_service()" in orchestrator,
    "orchestrator-soft-compiler": "apply_design_intent(" in orchestrator,
    "api-exposes-intent-both-branches": (route.count('"architectural_intent": (') == 2),
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Phase 26A integration checks failed: " + ", ".join(failed))

print("Phase 26A architectural intelligence integration: OK")
