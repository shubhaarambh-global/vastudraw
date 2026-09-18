from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase28_files_exist() -> None:
    assert (ROOT / "PHASE28_HYBRID_AI.md").is_file()
    assert (ROOT / "phase28-hybrid.env.example").is_file()
    assert (ROOT / "scripts/check-phase28-hybrid.py").is_file()
    assert (ROOT / "scripts/check-phase28-live.py").is_file()


def test_phase28_profile_has_no_secrets() -> None:
    text = (ROOT / "phase28-hybrid.env.example").read_text(encoding="utf-8")
    assert "OPENROUTER_API_KEY=\n" in text
    assert "GEMINI_API_KEY=\n" in text


def test_phase28_uses_direct_gemini() -> None:
    text = (ROOT / "phase28-hybrid.env.example").read_text(encoding="utf-8")
    assert "AI_VASTU_PLAN_RECOGNITION_PROVIDER=gemini" in text
    assert "AI_VASTU_PLAN_RECOGNITION_MODEL=gemini-3.1-flash-lite" in text


def test_phase28_uses_deepseek_text() -> None:
    text = (ROOT / "phase28-hybrid.env.example").read_text(encoding="utf-8")
    model = "deepseek/deepseek-v4-flash-0731:free"
    assert f"AI_VASTU_OPENROUTER_PRIMARY_MODEL={model}" in text
    assert "AI_VASTU_OPENROUTER_FALLBACK_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free" in text
