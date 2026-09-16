from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase16_adds_no_new_runtime_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "ai_vastu.generation" not in pyproject


def test_generation_api_uses_orchestration_service_not_duplicate_solver_logic() -> None:
    source = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
    assert '"/generation/architectural"' in source
    assert "generate_architectural_plan" in source
    assert "solve_rectangular_problem" not in source
    assert "build_architectural_geometry" not in source


def test_release_gate_stays_blocked_after_generation_api_is_completed() -> None:
    source = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
    assert "GENERATION_API_IMPLEMENTED" in source
    assert "AUTHORIZATION_IMPLEMENTED" in source
    assert "PRODUCTION_PERSISTENCE_IMPLEMENTED" in source
    assert "WEB_API_WORKFLOW_IMPLEMENTED" in source
