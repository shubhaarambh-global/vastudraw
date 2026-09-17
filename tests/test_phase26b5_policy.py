from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase26b5_uploaded_plan_pipeline_is_nonauthoritative() -> None:
    models = (ROOT / "python/ai_vastu/generation_intake/models.py").read_text(encoding="utf-8")
    plan_models = (ROOT / "python/ai_vastu/plan_intake/models.py").read_text(encoding="utf-8")

    assert 'DXF = "DXF"' in models
    assert 'DWG = "DWG"' in models
    assert "provisional: Literal[True] = True" in plan_models
    assert "requires_user_confirmation" in plan_models
    assert "confirmed_by_user: Literal[True]" in plan_models


def test_phase26b5_vastu_audit_is_soft_and_source_backed() -> None:
    audit = (ROOT / "python/ai_vastu/plan_intake/audit.py").read_text(encoding="utf-8")

    assert "load_soft_vastu_catalog" in audit
    assert "No Phase 26B.5 Vastu rule is a hard geometric constraint." in audit
    assert "No score is fabricated when true North is unknown." in audit


def test_phase26b5_generation_ui_exposes_plan_analysis() -> None:
    page = (ROOT / "apps/web/src/components/generation/GenerationWorkspacePage.tsx").read_text(
        encoding="utf-8"
    )

    for token in (
        ".dxf",
        ".dwg",
        "Analyze uploaded plan",
        "Uploaded-plan Vastu audit",
        "Confirmation required",
    ):
        assert token in page


def test_plan_intake_keeps_ezdxf_behind_exporting_adapter() -> None:
    root = Path(__file__).resolve().parents[1]

    intake_source = (root / "python" / "ai_vastu" / "plan_intake" / "cad.py").read_text(
        encoding="utf-8"
    )

    adapter_source = (root / "python" / "ai_vastu" / "exporting" / "dxf_importer.py").read_text(
        encoding="utf-8"
    )

    assert "import ezdxf" not in intake_source
    assert "from ezdxf" not in intake_source
    assert "summarize_dxf_bytes" in intake_source
    assert "import ezdxf" in adapter_source
