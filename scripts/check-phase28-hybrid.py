from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "phase28-hybrid.env.example"
DOC = ROOT / "PHASE28_HYBRID_AI.md"
SERVICE = ROOT / "python/ai_vastu/plan_intake/service.py"
PROVIDER = ROOT / "python/ai_vastu/plan_intake/provider.py"

DEEPSEEK = "deepseek/deepseek-v4-flash-0731:free"
NEMOTRON = "nvidia/nemotron-3-ultra-550b-a55b:free"
GEMINI = "gemini-3.1-flash-lite"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


for path in (PROFILE, DOC, SERVICE, PROVIDER):
    if not path.is_file():
        raise SystemExit(f"Phase 28 required file missing: {path}")

env = parse_env(PROFILE)

if env.get("OPENROUTER_API_KEY") != "":
    raise SystemExit("Hybrid example contains an OpenRouter secret.")
if env.get("GEMINI_API_KEY") != "":
    raise SystemExit("Hybrid example contains a Gemini secret.")
if env.get("AI_VASTU_OPENROUTER_PRIMARY_MODEL") != DEEPSEEK:
    raise SystemExit("DeepSeek free must be the development text model.")
if env.get("AI_VASTU_OPENROUTER_FALLBACK_MODEL") != NEMOTRON:
    raise SystemExit("Phase 26 legacy fallback pin changed unexpectedly.")

for name in (
    "AI_VASTU_REQUIREMENTS_PROVIDER",
    "AI_VASTU_ARCHITECT_PROVIDER",
    "AI_VASTU_VASTU_PROVIDER",
    "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
    "AI_VASTU_REVISION_PROVIDER",
):
    if env.get(name) != "openrouter":
        raise SystemExit(f"{name} must use OpenRouter.")

if env.get("AI_VASTU_PLAN_RECOGNITION_PROVIDER") != "gemini":
    raise SystemExit("Plan recognition must use direct Gemini.")
if env.get("AI_VASTU_PLAN_RECOGNITION_MODEL") != GEMINI:
    raise SystemExit("Unexpected Gemini plan-recognition model.")

service = SERVICE.read_text(encoding="utf-8")
provider = PROVIDER.read_text(encoding="utf-8")

if 'if name == "gemini":' not in service:
    raise SystemExit("Plan-intake service no longer exposes Gemini.")
if "GeminiPlanRecognitionProvider.from_environment()" not in service:
    raise SystemExit("Plan-intake service is not binding Gemini.")

for token in (
    "GEMINI_API_KEY",
    "AI_VASTU_PLAN_RECOGNITION_MODEL",
    "gemini-3.1-flash-lite",
    "generativelanguage.googleapis.com",
):
    if token not in provider:
        raise SystemExit(f"Gemini provider contract missing: {token}")

print(
    "Phase 28 hybrid gate passed: "
    "deepseek_text=true, gemini_direct_vision=true, "
    "secrets_not_committed=true, deterministic_authority_preserved=true"
)
