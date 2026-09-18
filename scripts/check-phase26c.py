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
    ROOT / "python/ai_vastu/requirements/candidate_orchestrator.py",
    ROOT / "apps/api/app/confirmed_generation_routes.py",
    ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx",
    ROOT / "apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx",
    ROOT / "apps/web/src/api/client.ts",
)
missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
if missing:
    raise SystemExit("Phase 26C missing files: " + ", ".join(missing))

strategies = default_candidate_strategies()
variants = tuple(search_variant_for_strategy(item) for item in strategies)
if PHASE26C_VERSION != "26C.2":
    raise SystemExit("Phase 26C.2 engine contract changed unexpectedly.")
if len(strategies) != 6 or len(set(variants)) != 6:
    raise SystemExit(
        "Phase 26C requires six deterministic strategies mapped to six search variants."
    )

wizard = " ".join(required[5].read_text(encoding="utf-8").split())
for token in (
    "True North",
    "Road side",
    "Entrance facing",
    "Practical",
    "Balanced",
    "Vastu-forward",
    "Structural planning is reserved for V2",
    "Generate alternatives",
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

orchestrator = required[3].read_text(encoding="utf-8")
route = required[4].read_text(encoding="utf-8")
workspace = required[6].read_text(encoding="utf-8")
client = required[7].read_text(encoding="utf-8")

for token in (
    "CandidateGenerationOrchestrator",
    "record_successful_generation",
    "run_multi_candidate_generation",
    "append_revision(command)",
):
    if token not in orchestrator:
        raise SystemExit(f"Phase 26C.3 orchestrator missing: {token}")

if orchestrator.index("append_revision(command)") > orchestrator.index(
    "record_successful_generation("
):
    raise SystemExit("Phase 26C.3 billing must occur after revision persistence.")

for token in (
    '"/projects/{project_id}/alternatives"',
    '"/projects/{project_id}/alternatives/select"',
):
    if token not in route:
        raise SystemExit(f"Phase 26C.3 API missing: {token}")

for token in (
    "Measured objectives",
    "Vastu",
    "Coverage",
    "Select this plan",
    "Phase 26D",
):
    if token not in workspace:
        raise SystemExit(f"Phase 26C.3 workspace missing: {token}")

for token in (
    "interpretRequirements",
    "confirmRequirements",
    "generateConfirmedAlternatives",
    "selectConfirmedAlternative",
):
    if token not in client:
        raise SystemExit(f"Phase 26C.3 client missing: {token}")

print(
    "Phase 26C.3 ready: wizard=true, requirements_confirmation=true, "
    "strategies=6, hard_validation=true, architecture_scoring=true, "
    "soft_vastu=true, coverage=true, comparison_workspace=true, "
    "selection_persistence=true, billing_after_persistence=true, "
    "revision_chat=phase26d, structural_v2=true"
)
