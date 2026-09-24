from __future__ import annotations

from unittest.mock import MagicMock

from ai_vastu.billing import factory
from ai_vastu.production.settings import load_production_settings
from tests.production.test_settings import base_environment


def test_production_billing_normalizes_the_canonical_database_url(
    monkeypatch,
    tmp_path,
) -> None:
    environment = base_environment(tmp_path)
    environment["AI_VASTU_DATABASE_URL"] = (
        "  postgresql://db.example.test/vastu  "
    )
    settings = load_production_settings(environment)
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    repository = MagicMock()
    repository_factory = MagicMock(return_value=repository)
    monkeypatch.setattr(factory, "PostgresBillingRepository", repository_factory)

    assert factory.create_billing_repository() is repository
    repository_factory.assert_called_once_with(settings.database_url)
