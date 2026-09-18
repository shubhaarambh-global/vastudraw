from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase26c3_preview_and_selection_are_separate() -> None:
    route = (ROOT / "apps/api/app/confirmed_generation_routes.py").read_text(encoding="utf-8")
    orchestrator = (ROOT / "python/ai_vastu/requirements/candidate_orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert '"/projects/{project_id}/alternatives"' in route
    assert '"/projects/{project_id}/alternatives/select"' in route
    assert "run_architectural_brain_candidates" in orchestrator

    candidate_engine = (
        ROOT / "python" / "ai_vastu" / "architectural_brain" / "candidate_engine.py"
    ).read_text(encoding="utf-8")

    assert "run_multi_candidate_generation" in candidate_engine
    assert orchestrator.index("append_revision(command)") < orchestrator.index(
        "record_successful_generation("
    )


def test_phase26c3_ui_binds_wizard_to_candidate_workspace() -> None:
    wizard = (ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx").read_text(
        encoding="utf-8"
    )
    workspace = (
        ROOT / "apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx"
    ).read_text(encoding="utf-8")
    client = (ROOT / "apps/web/src/api/client.ts").read_text(encoding="utf-8")

    assert "interpretRequirements" in wizard
    assert "confirmRequirements" in wizard
    assert "generateConfirmedAlternatives" in wizard
    assert "Phase26CCandidateWorkspace" in wizard
    assert "Select this plan" in workspace
    assert "Measured objectives" in workspace
    assert "Vastu" in workspace
    assert "Coverage" in workspace
    assert "selectConfirmedAlternative" in client


def test_phase26c3_keeps_revision_chat_and_structure_outside_v1() -> None:
    wizard = (ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx").read_text(
        encoding="utf-8"
    )
    workspace = (
        ROOT / "apps/web/src/components/generation/Phase26CCandidateWorkspace.tsx"
    ).read_text(encoding="utf-8")

    assert "Structural planning is reserved for V2" in " ".join(wizard.split())
    assert "Phase 26D" in workspace
