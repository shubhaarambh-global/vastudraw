from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = {
    "gemini_provider": (
        ROOT / "python/ai_vastu/requirements/providers/gemini_generate_content.py",
        'name = "gemini"',
    ),
    "gemini_model": (
        ROOT / "python/ai_vastu/production/settings.py",
        "AI_VASTU_GEMINI_MODEL",
    ),
    "single_price": (
        ROOT / "python/ai_vastu/billing/catalog.py",
        "amount_paise=49_900",
    ),
    "pack_price": (
        ROOT / "python/ai_vastu/billing/catalog.py",
        "amount_paise=489_900",
    ),
    "monthly_price": (
        ROOT / "python/ai_vastu/billing/catalog.py",
        "amount_paise=999_900",
    ),
    "yearly_price": (
        ROOT / "python/ai_vastu/billing/catalog.py",
        "amount_paise=6_999_900",
    ),
    "single_limit_metadata": (
        ROOT / "python/ai_vastu/billing/catalog.py",
        "generation_limit_per_project=3",
    ),
    "pack_limit_metadata": (
        ROOT / "python/ai_vastu/billing/catalog.py",
        "generation_limit_per_project=5",
    ),
}

missing = []
for name, (path, needle) in checks.items():
    if not path.is_file() or needle not in path.read_text(encoding="utf-8"):
        missing.append(name)

if missing:
    raise SystemExit("Launch Gemini/pricing check failed: " + ", ".join(missing))

print(
    "Launch Gemini/pricing wired: gemini_2_5_flash=true, "
    "single_499=true, single_limit_metadata=3, pack_4899=true, "
    "pack_limit_metadata=5, monthly_9999=true, yearly_69999=true"
)
