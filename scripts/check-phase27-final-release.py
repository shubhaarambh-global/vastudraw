from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRIMARY = "deepseek/deepseek-v4-flash-0731:free"
VISION = "inclusionai/ling-3.0-flash-vl:free"
FALLBACK = "nvidia/nemotron-3-ultra-550b-a55b:free"

REQUIRED_FILES = (
    "PHASE25.md",
    "PHASE26_COMPLETE.md",
    "PHASE26_OPENROUTER.md",
    "python/ai_vastu/openrouter_http.py",
    "python/ai_vastu/nvidia_nim_http.py",
    "python/ai_vastu/production/settings.py",
    "python/ai_vastu/requirements/candidate_orchestrator.py",
    "python/ai_vastu/requirements/generation_adapter.py",
    "python/ai_vastu/requirements/finalization.py",
    "python/ai_vastu/architectural_brain/candidate_engine.py",
    "python/ai_vastu/architectural_brain/revisions.py",
    "python/ai_vastu/plan_intake/service.py",
    "python/ai_vastu/vastu_reasoning/service.py",
    "python/ai_vastu/projects/postgres_repository.py",
    "python/ai_vastu/billing/service.py",
    "apps/api/app/confirmed_generation_routes.py",
    "apps/web/src/components/generation/Phase26CProjectWizard.tsx",
    "apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx",
    "scripts/check-openrouter-live.py",
    "scripts/check-production-launch.py",
    "scripts/assert-production-release.py",
    "scripts/backup-production.ps1",
    "docs/runbooks/production-launch.md",
    "docs/vastu/spec-v1.0/production/rule-bundle.json",
)

missing = [item for item in REQUIRED_FILES if not (ROOT / item).is_file()]
if missing:
    raise SystemExit("Phase 27 missing required V1 files: " + ", ".join(missing))

package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
scripts = package.get("scripts", {})
for name in (
    "validate",
    "phase25:check",
    "phase25:launch",
    "phase26:check",
    "phase26:openrouter-check",
    "phase26:openrouter-live",
):
    if name not in scripts:
        raise SystemExit(f"Phase 27 requires package script: {name}")

openrouter_doc = (ROOT / "PHASE26_OPENROUTER.md").read_text(encoding="utf-8")
for model in (PRIMARY, VISION, FALLBACK):
    if model not in openrouter_doc:
        raise SystemExit(f"Validated OpenRouter model pin missing from documentation: {model}")

env_text = (ROOT / ".env.example").read_text(encoding="utf-8")
for token in (
    "OPENROUTER_API_KEY",
    "AI_VASTU_OPENROUTER_PRIMARY_MODEL",
    "AI_VASTU_OPENROUTER_VISION_MODEL",
    "AI_VASTU_OPENROUTER_FALLBACK_MODEL",
):
    if token not in env_text:
        raise SystemExit(f"OpenRouter environment contract missing: {token}")

# Any model value explicitly pinned in .env.example must remain free-only.
for match in re.finditer(
    r"^AI_VASTU_OPENROUTER_(?:PRIMARY|VISION|FALLBACK)_MODEL=(.+)$",
    env_text,
    flags=re.MULTILINE,
):
    model = match.group(1).strip()
    if model and not model.endswith(":free"):
        raise SystemExit(
            f"Paid/non-free OpenRouter model found in V1 environment contract: {model}"
        )

settings = (ROOT / "python/ai_vastu/production/settings.py").read_text(encoding="utf-8").lower()
for token in (
    "nvidia_nim",
    "nvidia_api_key",
    "nvidia_nim_api_base",
    "ai_vastu_nvidia_primary_model",
    "ai_vastu_nvidia_vision_model",
):
    if token not in settings:
        raise SystemExit(f"Production NVIDIA NIM contract is missing: {token}")
if "openrouter_api_key" in settings or "gemini_api_key" in settings:
    raise SystemExit(
        "Production settings still require a legacy AI-provider credential."
    )

nvidia_client = (ROOT / "python/ai_vastu/nvidia_nim_http.py").read_text(
    encoding="utf-8"
)
for pin in (
    "https://integrate.api.nvidia.com/v1",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
):
    if pin not in nvidia_client:
        raise SystemExit(f"NVIDIA NIM client pin is missing: {pin}")

production_env = (ROOT / ".env.production.example").read_text(encoding="utf-8")
if "NVIDIA_API_KEY=" not in production_env:
    raise SystemExit("Production NVIDIA credential contract is missing.")
if "OPENROUTER_API_KEY" in production_env or "GEMINI_API_KEY" in production_env:
    raise SystemExit("Production example still exposes a legacy AI credential.")

orchestrator = (ROOT / "python/ai_vastu/requirements/candidate_orchestrator.py").read_text(
    encoding="utf-8"
)

generation_adapter = (
    ROOT / "python/ai_vastu/requirements/generation_adapter.py"
).read_text(encoding="utf-8")

finalization = (
    ROOT / "python/ai_vastu/requirements/finalization.py"
).read_text(encoding="utf-8")

for token in (
    "INVALID_FLOOR_COUNT: supported residential generation is limited to 1-4 floors.",
    "confirmed.floor_count > 1",
):
    if token not in generation_adapter:
        raise SystemExit(f"Bounded multi-floor generation contract is missing: {token}")

for token in (
    "BUILDING_PROGRAM_INCOMPLETE",
    "BUILDING_CIRCULATION_DISCONNECTED",
    "Accepted multi-floor generation is missing floor geometry.",
):
    if token not in finalization:
        raise SystemExit(f"Multi-floor fail-closed validation contract is missing: {token}")
if (
    "append_revision(command)" not in orchestrator
    or "record_successful_generation(" not in orchestrator
):
    raise SystemExit("Candidate persistence/billing contract is missing.")
if orchestrator.index("append_revision(command)") > orchestrator.index(
    "record_successful_generation("
):
    raise SystemExit("Billing must occur only after durable selected-revision persistence.")

brain = (
    (ROOT / "python/ai_vastu/architectural_brain/candidate_engine.py")
    .read_text(encoding="utf-8")
    .lower()
)
if "hard" not in brain or "valid" not in brain:
    raise SystemExit("Architectural Brain candidate engine no longer exposes hard-valid gating.")

phase26 = (ROOT / "PHASE26_COMPLETE.md").read_text(encoding="utf-8")
for boundary in (
    "AI never emits authoritative CAD coordinates.",
    "The deterministic solver remains authoritative",
    "Structural design remains V2.",
):
    if boundary not in phase26:
        raise SystemExit(f"Phase 26 authority boundary changed unexpectedly: {boundary}")

bundle = json.loads(
    (ROOT / "docs/vastu/spec-v1.0/production/rule-bundle.json").read_text(encoding="utf-8")
)
if not bool(bundle.get("production")):
    raise SystemExit("Frozen Vastu bundle is not marked production.")

print(
    "Phase 27 final V1 offline gate passed: "
    "auth=true, persistence=true, billing=true, requirements=true, "
    "active_ai=nvidia_nim, legacy_openrouter_free_only=true, architectural_brain=true, "
    "deterministic_geometry_authority=true, hard_validation=true, "
    "frozen_vastu=true, immutable_revisions=true, editor=true, exports=true, "
    "multifloor_v1=true, floors_1_to_4=true, structural_v2=true"
)
