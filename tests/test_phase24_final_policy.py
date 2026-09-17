from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_free_generation_is_recorded_after_revision_commit() -> None:
    source = (ROOT / "python/ai_vastu/requirements/final_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert source.index("append_revision(command)") < source.index("record_successful_generation(")


def test_project_ownership_precedes_entitlement_authorization() -> None:
    source = (ROOT / "python/ai_vastu/requirements/final_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert source.index("is_project_owner(") < source.index("authorize_generation(")


def test_phase24_uses_frozen_repository_vastu_bundle() -> None:
    source = (ROOT / "python/ai_vastu/requirements/finalization.py").read_text(encoding="utf-8")
    assert "rule-bundle.json" in source
    assert "b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667" in source


def test_phase24_fails_closed_on_multifloor_generation() -> None:
    source = (ROOT / "python/ai_vastu/requirements/final_orchestrator.py").read_text(
        encoding="utf-8"
    )
    assert "confirmed.floor_count != 1" in source
    assert "room.floor_preference not in {None, 0}" in source
