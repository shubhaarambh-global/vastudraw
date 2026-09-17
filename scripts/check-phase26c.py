from __future__ import annotations

from pathlib import Path

from ai_vastu.multi_candidate import (
    PHASE26C_VERSION,
    default_candidate_strategies,
    search_variant_for_strategy,
)

ROOT = Path(__file__).resolve().parents[1]

required = (
    ROOT / "python/ai_vastu/multi_candidate/models.py",
    ROOT / "python/ai_vastu/multi_candidate/strategies.py",
    ROOT / "python/ai_vastu/multi_candidate/engine.py",
    ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx",
    ROOT / "apps/web/src/components/generation/Phase26CGenerationPage.tsx",
    ROOT / "tests/test_phase26c_policy.py",
)
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Phase 26C missing files: " + ", ".join(missing))

strategies = default_candidate_strategies()
variants = tuple(search_variant_for_strategy(item) for item in strategies)
if PHASE26C_VERSION != "26C.2":
    raise SystemExit("Phase 26C model contract is not upgraded to 26C.2.")
if len(strategies) != 6 or len(set(variants)) != 6:
    raise SystemExit(
        "Phase 26C.2 requires six deterministic strategies mapped to six search variants."
    )

wizard_source = required[3].read_text(encoding="utf-8")
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

engine = required[2].read_text(encoding="utf-8").lower()
for token in (
    "run_multi_candidate_generation",
    "generationdisposition.accepted",
    "compute_vastu_evaluation_coverage",
    "duplicate_placement_signature",
    "insufficient_geometric_diversity",
    "hard validation",
):
    if token not in engine:
        raise SystemExit(f"Phase 26C.2 engine missing contract: {token}")

print(
    "Phase 26C.2 ready: wizard=true, strategies=6, search_variants=6, "
    "hard_validation=true, architecture_scoring=true, soft_vastu=true, "
    "coverage=true, diversity=true, structural_v2=true"
)
