from __future__ import annotations

from pathlib import Path

from ai_vastu.openrouter_http import (
    APPROVED_FREE_MODELS,
    FALLBACK_REASONING_MODEL,
    FREE_PDF_PLUGIN,
    PRIMARY_ARCHITECTURAL_MODEL,
    VISION_PLAN_MODEL,
    OpenRouterModelPolicy,
)

ROOT = Path(__file__).resolve().parents[1]

expected = {
    "deepseek/deepseek-v4-flash-0731:free",
    "inclusionai/ling-3.0-flash-vl:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
}
if set(APPROVED_FREE_MODELS) != expected:
    raise SystemExit("OpenRouter approved-free model set drifted.")
if any(not item.endswith(":free") for item in APPROVED_FREE_MODELS):
    raise SystemExit("OpenRouter model policy contains a non-:free model.")
if "openrouter/free" in APPROVED_FREE_MODELS:
    raise SystemExit("Random OpenRouter free router is not allowed.")

policy = OpenRouterModelPolicy()
policy.validate()
if policy.primary != PRIMARY_ARCHITECTURAL_MODEL:
    raise SystemExit("Primary Architectural Brain model drifted.")
if policy.vision != VISION_PLAN_MODEL:
    raise SystemExit("Vision plan-reader model drifted.")
if policy.fallback != FALLBACK_REASONING_MODEL:
    raise SystemExit("Fallback reasoning model drifted.")

plugin_text = repr(FREE_PDF_PLUGIN)
if "cloudflare-ai" not in plugin_text:
    raise SystemExit("PDF parsing is not pinned to the free Cloudflare engine.")
if "mistral" in plugin_text.lower():
    raise SystemExit("Paid/default PDF OCR fallback must not be configured.")

required = {
    "http": ROOT / "python/ai_vastu/openrouter_http.py",
    "requirements": ROOT / "python/ai_vastu/requirements/providers/openrouter_chat.py",
    "architect": ROOT / "python/ai_vastu/architectural_intelligence/providers/openrouter.py",
    "vastu": ROOT / "python/ai_vastu/vastu_reasoning/providers/openrouter.py",
    "vision": ROOT / "python/ai_vastu/plan_intake/openrouter_provider.py",
    "brain": ROOT / "python/ai_vastu/architectural_brain/provider.py",
    "brain_service": ROOT / "python/ai_vastu/architectural_brain/service.py",
    "candidate_engine": ROOT / "python/ai_vastu/architectural_brain/candidate_engine.py",
    "revisions": ROOT / "python/ai_vastu/architectural_brain/revisions.py",
}
for label, path in required.items():
    if not path.is_file():
        raise SystemExit(f"OpenRouter integration missing {label}: {path.relative_to(ROOT)}")

brain_source = required["brain"].read_text(encoding="utf-8")
service_source = required["brain_service"].read_text(encoding="utf-8")
candidate_source = required["candidate_engine"].read_text(encoding="utf-8")
vision_source = required["vision"].read_text(encoding="utf-8")
vastu_source = required["vastu"].read_text(encoding="utf-8")

for token in (
    "width_mm",
    "depth_mm",
    "bedroom_count",
    "toilet_count",
    "parking_count",
    "road_side",
    "entrance_side",
):
    if token not in brain_source or token not in service_source:
        raise SystemExit(f"Architectural Brain lost confirmed site/program context: {token}")

if "run_multi_candidate_generation" not in candidate_source:
    raise SystemExit("Deterministic multi-candidate geometry engine is no longer downstream.")
if "authoritative_geometry" not in brain_source or "False" not in brain_source:
    raise SystemExit("Architectural Brain authority boundary is missing.")
if "OpenRouterPlanRecognitionProvider" not in vision_source:
    raise SystemExit("OpenRouter vision plan reader is not wired.")
if "Cloudflare" not in vision_source:
    raise SystemExit("Vision/PDF free-parser warning is missing.")
if "Vastu is a SOFT design influence only" not in vastu_source:
    raise SystemExit("Soft-Vastu authority policy drifted.")

print(
    "Phase 26 OpenRouter wired: free_only=true, "
    "primary=deepseek-v4-flash-0731:free, "
    "vision=ling-3.0-flash-vl:free, "
    "fallback=nemotron-3-ultra-550b-a55b:free, "
    "paid_fallback=false, deterministic_geometry=true"
)
