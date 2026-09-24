from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient

from ai_vastu.auth import AuthenticationError, SupabaseAccessTokenVerifier
from ai_vastu.auth import verifier as verifier_module
from app.main import create_app

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = "33333333-3333-3333-3333-333333333333"
INTAKE = "55555555-5555-5555-5555-555555555555"
ISSUER = "https://fixture-project.supabase.co/auth/v1"


@pytest.fixture
def signing_key() -> Any:
    from cryptography.hazmat.primitives.asymmetric import rsa

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _verifier(monkeypatch: pytest.MonkeyPatch, signing_key: Any) -> SupabaseAccessTokenVerifier:
    monkeypatch.setattr(
        verifier_module.jwt_api,
        "PyJWKClient",
        lambda _url: SimpleNamespace(
            get_signing_key_from_jwt=lambda _token: SimpleNamespace(key=signing_key.public_key())
        ),
    )
    return SupabaseAccessTokenVerifier("https://fixture-project.supabase.co")


def _token(signing_key: Any, overrides: dict[str, Any] | None = None) -> str:
    claims: dict[str, Any] = {
        "sub": str(USER),
        "role": "authenticated",
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides or {})
    if overrides is not None and overrides.get("exp", "present") is None:
        claims.pop("exp")
    return jwt.encode(claims, signing_key, algorithm="RS256")


@pytest.mark.parametrize(
    ("claims", "algorithm"),
    [
        ({"exp": None}, "RS256"),
        ({"exp": int(time.time()) - 60}, "RS256"),
        ({"role": "service_role"}, "RS256"),
        ({"iss": "https://attacker.invalid/auth/v1"}, "RS256"),
        ({"aud": "anon"}, "RS256"),
        ({"sub": "not-a-uuid"}, "RS256"),
        ({"exp": float("inf")}, "RS256"),
        ({}, "HS256"),
    ],
    ids=[
        "missing-exp",
        "expired",
        "wrong-role",
        "wrong-issuer",
        "wrong-audience",
        "malformed-subject",
        "non-finite-expiry",
        "wrong-algorithm",
    ],
)
def test_supabase_verifier_rejects_invalid_signed_claim_fixtures(
    monkeypatch: pytest.MonkeyPatch,
    signing_key: Any,
    claims: dict[str, Any],
    algorithm: str,
) -> None:
    verifier = _verifier(monkeypatch, signing_key)
    if algorithm == "HS256":
        token = jwt.encode(
            {
                "sub": str(USER),
                "role": "authenticated",
                "iss": ISSUER,
                "aud": "authenticated",
                "exp": int(time.time()) + 3600,
            },
            "offline-fixture-secret-32-bytes-minimum",
            algorithm=algorithm,
        )
    else:
        token = _token(signing_key, claims)
    with pytest.raises(AuthenticationError):
        verifier.verify(token)


def test_supabase_verifier_accepts_minimal_canonical_claims(
    monkeypatch: pytest.MonkeyPatch, signing_key: Any
) -> None:
    verifier = _verifier(monkeypatch, signing_key)
    user = verifier.verify(_token(signing_key, {"email": "fixture@example.invalid"}))
    assert user.user_id == USER
    assert user.role == "authenticated"
    assert user.email == "fixture@example.invalid"


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", f"/projects/{PROJECT}/generation-intakes", {}),
        ("get", f"/projects/{PROJECT}/generation-intakes/{INTAKE}", {}),
        ("post", "/generation/architectural", {"json": {}}),
    ],
)
def test_auxiliary_generation_routes_use_injected_verifier(
    method: str,
    path: str,
    kwargs: dict[str, Any],
) -> None:
    from unittest.mock import MagicMock

    verifier = MagicMock()
    verifier.verify.side_effect = AuthenticationError("fixture rejected")
    repository = MagicMock()
    intake_store = MagicMock()
    client = TestClient(
        create_app(
            repository=repository,
            access_token_verifier=verifier,
            generation_intake_store=intake_store,
        )
    )

    response = client.request(
        method,
        path,
        headers={"Authorization": "Bearer injected-token"},
        **kwargs,
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    verifier.verify.assert_called_once_with("injected-token")
    repository.is_project_owner.assert_not_called()
    intake_store.get.assert_not_called()
    intake_store.list_for_project.assert_not_called()
