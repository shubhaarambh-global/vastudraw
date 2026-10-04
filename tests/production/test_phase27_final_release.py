from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_phase27_final_release_files_exist() -> None:
    assert (ROOT / "PHASE27_FINAL_RELEASE.md").is_file()
    assert (ROOT / "docs/runbooks/final-v1-release.md").is_file()
    assert (ROOT / "scripts/check-phase27-final-release.py").is_file()
    assert (ROOT / "scripts/check-phase27-live.py").is_file()


def test_phase27_live_gate_is_fail_closed_and_reuses_existing_gates() -> None:
    source = (ROOT / "scripts/check-phase27-live.py").read_text(encoding="utf-8")
    assert "check-phase29c-live.py" in source
    assert "check-production-launch.py" in source
    assert "production_qualification=false" in source
    assert "RELEASE QUALIFICATION PASSED" not in source
    hybrid_source = (ROOT / "scripts/check-phase29c-live.py").read_text(encoding="utf-8")
    assert "NVIDIA TEXT PRIMARY" in hybrid_source
    assert "NVIDIA VISION PDF-PATH" in hybrid_source
    assert "PHASE29C NVIDIA_NIM BLOCKED_CREDENTIALS" in hybrid_source
    assert "OPENROUTER_API_KEY" not in hybrid_source
    assert "GEMINI_API_KEY" not in hybrid_source
    assert "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER" in hybrid_source


def test_phase27_does_not_claim_v2_scope() -> None:
    source = (ROOT / "PHASE27_FINAL_RELEASE.md").read_text(encoding="utf-8")
    assert "Structural engineering and multi-floor generation remain V2 scope" in source
    assert "AI output is non-authoritative for exact CAD geometry" in source
