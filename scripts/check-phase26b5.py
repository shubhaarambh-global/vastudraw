from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "models": ROOT / "python/ai_vastu/plan_intake/models.py",
    "provider": ROOT / "python/ai_vastu/plan_intake/provider.py",
    "audit": ROOT / "python/ai_vastu/plan_intake/audit.py",
    "api": ROOT / "apps/api/app/main.py",
    "client": ROOT / "apps/web/src/api/client.ts",
    "page": ROOT / "apps/web/src/components/generation/GenerationWorkspacePage.tsx",
    "intake": ROOT / "python/ai_vastu/generation_intake/store.py",
}

for label, path in FILES.items():
    if not path.is_file():
        raise SystemExit(f"Phase 26B.5 missing {label}: {path.relative_to(ROOT)}")

models = FILES["models"].read_text(encoding="utf-8")
provider = FILES["provider"].read_text(encoding="utf-8")
audit = FILES["audit"].read_text(encoding="utf-8")
api = FILES["api"].read_text(encoding="utf-8")
page = FILES["page"].read_text(encoding="utf-8")
intake = FILES["intake"].read_text(encoding="utf-8")

checks = {
    "jpg_png_pdf": all(token in page for token in (".jpg", ".png", ".pdf")),
    "dxf_dwg": all(token in intake for token in ('".dxf"', '".dwg"')),
    "gemini_recognition": "GeminiPlanRecognitionProvider" in provider,
    "cad_summary": "summarize_dxf" in provider,
    "dwg_adapter": "convert_dwg_to_dxf" in provider,
    "soft_vastu_audit": "load_soft_vastu_catalog" in audit,
    "provisional_score": "provisional: Literal[True]" in models,
    "no_fake_north_score": "NEEDS_ORIENTATION" in audit,
    "exact_envelope_confirmation": "PlanGeometryConfirmationRecord" in models,
    "api_analysis": "plan-analysis" in api,
    "nonauthoritative": "authoritative_geometry=False"
    in (ROOT / "python/ai_vastu/generation_intake/store.py").read_text(encoding="utf-8"),
}

failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit(f"Phase 26B.5 integration checks failed: {failed}")

print(
    "Phase 26B.5 plan intake + Vastu audit wired: " + ", ".join(f"{name}=true" for name in checks)
)
