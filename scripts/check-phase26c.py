from __future__ import annotations

from pathlib import Path

from ai_vastu.multi_candidate.strategies import default_candidate_strategies

ROOT = Path(__file__).resolve().parents[1]

required = (
    ROOT / "python/ai_vastu/multi_candidate/models.py",
    ROOT / "python/ai_vastu/multi_candidate/strategies.py",
    ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx",
    ROOT / "apps/web/src/components/generation/Phase26CGenerationPage.tsx",
    ROOT / "tests/test_phase26c_policy.py",
)
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Phase 26C.1 missing files: " + ", ".join(missing))

strategies = default_candidate_strategies()
if len(strategies) != 6:
    raise SystemExit("Phase 26C deterministic strategy catalogue must contain six strategies.")

wizard_source = required[2].read_text(encoding="utf-8")
wizard = " ".join(wizard_source.split())

for token in (
    "True North",
    "Road side",
    "Entrance facing",
    "Practical",
    "Balanced",
    "Vastu-forward",
    "Structural planning is reserved for V2",
):
    if token not in wizard:
        raise SystemExit(f"Phase 26C wizard missing required UX contract: {token}")

print("Phase 26C.1 ready: wizard=true, candidate_contract=true, strategies=6, structural_v2=true")
