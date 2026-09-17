from __future__ import annotations

from pathlib import Path


def test_phase26a_never_creates_hard_vastu_or_ai_constraints() -> None:
    root = Path(__file__).resolve().parents[1]
    compiler = (
        root / "python" / "ai_vastu" / "architectural_intelligence" / "compiler.py"
    ).read_text(encoding="utf-8")
    gemini = (
        root / "python" / "ai_vastu" / "architectural_intelligence" / "providers" / "gemini.py"
    ).read_text(encoding="utf-8")

    assert "hard=True" not in compiler
    assert "hard=False" in compiler
    assert "soft preferences only" in compiler
    assert "Do NOT apply Vastu placement rules in Phase 26A" in gemini
    assert "Do NOT draw authoritative geometry" in gemini
