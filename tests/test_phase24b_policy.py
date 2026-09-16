from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase24b_calls_existing_generation_service() -> None:
    source = (
        ROOT / "python/ai_vastu/requirements/generation_adapter.py"
    ).read_text(encoding="utf-8")
    assert "ArchitecturalGenerationRequest" in source
    assert "generate_architectural_plan" in source
    assert "model_validate_json" in source
    assert "json.dumps(payload)" in source


def test_final_binding_claims_revision_only_after_canonical_commit() -> None:
    route = (
        ROOT / "apps/api/app/confirmed_generation_routes.py"
    ).read_text(encoding="utf-8")

    # Rejected/unsolved generations remain explicitly unpersisted.
    assert '"revision_persisted": False' in route

    # Accepted canonical generations may report persisted revision + Vastu.
    assert '"revision_persisted": True' in route
    assert '"vastu_analysis": canonical.vastu.model_dump(mode="json")' in route
    assert "run.revision is None or run.canonical is None" in route


def test_phase24b_requires_explicit_profile_acceptance() -> None:
    adapter = (
        ROOT / "python/ai_vastu/requirements/generation_adapter.py"
    ).read_text(encoding="utf-8")
    assert "accept_profile_defaults: Literal[True]" in adapter
