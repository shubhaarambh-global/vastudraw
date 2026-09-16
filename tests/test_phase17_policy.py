from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase17_web_workflow_does_not_relax_other_release_blockers() -> None:
    source = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
    assert "WEB_API_WORKFLOW_IMPLEMENTED" in source
    assert "WEB_API_WORKFLOW_NOT_IMPLEMENTED" not in source
    assert "AUTHORIZATION_IMPLEMENTED" in source
    assert "PRODUCTION_PERSISTENCE_IMPLEMENTED" in source
    assert "VASTU_SPEC_NOT_FROZEN" in source


def test_web_client_calls_existing_api_contracts_instead_of_reimplementing_backend() -> None:
    source = (ROOT / "apps/web/src/api/client.ts").read_text(encoding="utf-8")
    assert "/projects" in source
    assert "/generation/architectural" in source
    assert "solve_rectangular_problem" not in source
    assert "build_architectural_geometry" not in source


def test_phase17_generation_input_remains_explicit() -> None:
    source = (
        ROOT / "apps/web/src/components/editor/ProjectWorkflowPanel.tsx"
    ).read_text(encoding="utf-8")
    assert "Explicit ArchitecturalGenerationRequest JSON" in source
    assert "does not invent missing geometry or solver inputs" in source
