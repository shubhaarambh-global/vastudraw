from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase15_adds_no_new_runtime_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "ai_vastu.release" not in pyproject


def test_release_gate_does_not_claim_ready_by_default() -> None:
    source = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
    assert "VASTU_SPEC_NOT_FROZEN" in source
    assert "AUTHORIZATION_IMPLEMENTED" in source
    assert "WEB_API_WORKFLOW_NOT_IMPLEMENTED" not in source


def test_production_promotion_script_is_separate_from_ci_check() -> None:
    package = (ROOT / "package.json").read_text(encoding="utf-8")
    assert '"mvp:check"' in package
    assert '"mvp:release"' in package
