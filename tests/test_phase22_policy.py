from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase22_generation_intake_accepts_prompt_image_and_pdf() -> None:
    source = (ROOT / "apps/web/src/components/generation/GenerationWorkspacePage.tsx").read_text(
        encoding="utf-8"
    )
    assert "Generation prompt" in source
    assert "image/jpeg" in source
    assert "image/png" in source
    assert "application/pdf" in source
    assert "Save generation brief" in source


def test_phase22_reference_inputs_are_explicitly_nonauthoritative() -> None:
    source = (ROOT / "python/ai_vastu/generation_intake/models.py").read_text(encoding="utf-8")
    assert "authoritative_geometry: bool = False" in source
    assert "cannot be authoritative geometry" in source


def test_phase22_uploads_are_project_owned_and_authenticated() -> None:
    source = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
    assert '"/projects/{project_id}/generation-intakes"' in source
    assert "_require_project_owner(service, project_id, user)" in source
    assert "CurrentUserDependency" in source
