from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase25_middleware_protects_commercial_paths() -> None:
    source = (
        ROOT / "python/ai_vastu/production/middleware.py"
    ).read_text(encoding="utf-8")
    assert 'path == "/requirements/interpret"' in source
    assert 'path.startswith("/confirmed-generation/projects/")' in source
    assert 'path == "/billing/checkout"' in source
    assert "hash_rate_limit_key" in source


def test_launch_gate_rejects_dev_and_test_commerce_configuration() -> None:
    source = (
        ROOT / "python/ai_vastu/production/settings.py"
    ).read_text(encoding="utf-8")
    assert 'APP_ENV must be production' in source
    assert 'AI_VASTU_AUTH_MODE must be production' in source
    assert 'key_id.startswith("rzp_test_")' in source


def test_phase25_preserves_frozen_vastu_hash() -> None:
    source = (
        ROOT / "python/ai_vastu/production/settings.py"
    ).read_text(encoding="utf-8")
    assert (
        "b11b66be61d6436fcaa43c1c5b743c0090051154146d91caf904eb5108546667"
        in source
    )
