from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase24a_never_mutates_frozen_vastu_bundle() -> None:
    apply_source = (ROOT / "scripts/apply-phase24a.py").read_text(encoding="utf-8")
    assert "rule-bundle.json" not in apply_source
    assert "docs/vastu/spec-v1.0/production" not in apply_source


def test_phase24a_has_explicit_human_confirmation_boundary() -> None:
    models = (ROOT / "python/ai_vastu/requirements/models.py").read_text(encoding="utf-8")
    routes = (ROOT / "apps/api/app/requirements_routes.py").read_text(encoding="utf-8")

    assert "user_confirmed: Literal[True]" in models
    assert "/drafts/{draft_id}/confirm" in routes


def test_phase24a_live_model_is_not_guessed() -> None:
    provider = (ROOT / "python/ai_vastu/requirements/providers/openai_responses.py").read_text(
        encoding="utf-8"
    )
    assert "AI_VASTU_OPENAI_MODEL" in provider
    assert "no live model is guessed" in provider
