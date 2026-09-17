from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase26c_keeps_structural_design_out_of_v1() -> None:
    models = (ROOT / "python/ai_vastu/multi_candidate/models.py").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx").read_text(
        encoding="utf-8"
    )

    normalized_wizard = " ".join(wizard.split())

    assert "structural_design_included: Literal[False]" in models
    assert "Structural planning is reserved for V2" in normalized_wizard


def test_phase26c_wizard_distinguishes_orientation_concepts() -> None:
    wizard = (ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx").read_text(
        encoding="utf-8"
    )
    normalized_wizard = " ".join(wizard.split())

    for token in ("True North", "Road side", "Entrance facing"):
        assert token in normalized_wizard


def test_phase26c_exposes_three_vastu_influence_modes() -> None:
    wizard = (ROOT / "apps/web/src/components/generation/Phase26CProjectWizard.tsx").read_text(
        encoding="utf-8"
    )
    normalized_wizard = " ".join(wizard.split())

    for token in ("Practical", "Balanced", "Vastu-forward"):
        assert token in normalized_wizard
