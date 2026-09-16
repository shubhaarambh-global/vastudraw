from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase18_removes_only_persistence_release_blocker() -> None:
    source = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
    assert "PRODUCTION_PERSISTENCE_IMPLEMENTED" in source
    assert "PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED" not in source
    assert "AUTHORIZATION_IMPLEMENTED" in source
    assert "VASTU_SPEC_NOT_FROZEN" in source


def test_production_repository_uses_postgres_transaction_boundary() -> None:
    source = (ROOT / "python/ai_vastu/projects/postgres_repository.py").read_text(encoding="utf-8")
    assert "FOR UPDATE" in source
    assert "connection.transaction()" in source
    assert "prepare_threshold" in source
