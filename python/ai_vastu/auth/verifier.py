from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID

import jwt
from jwt.exceptions import PyJWTError

from .errors import AuthConfigurationError, AuthenticationError
from .models import AuthenticatedUser

# PyJWT exposes some runtime API through package re-exports; keep typing isolated.
jwt_api: Any = jwt

_PRODUCTION_ENVIRONMENTS = frozenset({"production", "staging"})
_ALLOWED_ASYMMETRIC_ALGORITHMS = ("ES256", "RS256")
_DEFAULT_DEV_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class AccessTokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


class DevelopmentAccessTokenVerifier:
    """Explicit development-only bearer token verifier.

    This verifier is intentionally unavailable in production/staging. It keeps local
    development deterministic without pretending a development token is a production
    authentication mechanism.
    """

    def __init__(self, token: str, user_id: UUID = _DEFAULT_DEV_USER_ID) -> None:
        if not token.strip():
            raise ValueError("Development bearer token cannot be blank.")
        self._token = token
        self._user = AuthenticatedUser(
            user_id=user_id,
            role="authenticated",
            email="developer@local.invalid",
        )

    def verify(self, token: str) -> AuthenticatedUser:
        if token != self._token:
            raise AuthenticationError("Invalid development access token.")
        return self._user


class SupabaseAccessTokenVerifier:
    """Verify Supabase Auth access tokens against asymmetric project signing keys."""

    def __init__(self, supabase_url: str) -> None:
        base_url = supabase_url.strip().rstrip("/")
        if not base_url.startswith("https://"):
            raise AuthConfigurationError("Supabase URL must use HTTPS.")
        self._issuer = f"{base_url}/auth/v1"
        jwks_url = f"{self._issuer}/.well-known/jwks.json"
        self._jwk_client: Any = jwt_api.PyJWKClient(jwks_url)

    def verify(self, token: str) -> AuthenticatedUser:
        if not token.strip():
            raise AuthenticationError("Bearer token cannot be blank.")
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            claims: dict[str, Any] = jwt_api.decode(
                token,
                signing_key.key,
                algorithms=list(_ALLOWED_ASYMMETRIC_ALGORITHMS),
                audience="authenticated",
                issuer=self._issuer,
                options={"require": ["exp", "iss", "sub", "role"]},
            )
            user_id = UUID(str(claims["sub"]))
            role = str(claims["role"])
            if role != "authenticated":
                raise AuthenticationError("Access token role is not authenticated.")
            email_value = claims.get("email")
            email = email_value if isinstance(email_value, str) else None
            return AuthenticatedUser(user_id=user_id, role=role, email=email)
        except AuthenticationError:
            raise
        except (PyJWTError, ValueError, KeyError, TypeError, OverflowError) as exc:
            raise AuthenticationError("Access token verification failed.") from exc


def create_access_token_verifier_from_environment(
    environment: Mapping[str, str] | None = None,
) -> AccessTokenVerifier:
    env = os.environ if environment is None else environment
    app_env = env.get("APP_ENV", "development").strip().lower()
    auth_mode = env.get("AI_VASTU_AUTH_MODE", "").strip().lower()
    supabase_url = env.get("AI_VASTU_SUPABASE_URL", "").strip()

    if auth_mode not in {"", "development", "supabase"}:
        raise AuthConfigurationError("AI_VASTU_AUTH_MODE must be 'development' or 'supabase'.")

    if app_env in _PRODUCTION_ENVIRONMENTS:
        if auth_mode == "development":
            raise AuthConfigurationError(
                "Development authentication is forbidden in production/staging."
            )
        if not supabase_url:
            raise AuthConfigurationError("AI_VASTU_SUPABASE_URL is required in production/staging.")
        return SupabaseAccessTokenVerifier(supabase_url)

    if auth_mode == "supabase" or supabase_url:
        if not supabase_url:
            raise AuthConfigurationError(
                "AI_VASTU_SUPABASE_URL is required when AI_VASTU_AUTH_MODE=supabase."
            )
        return SupabaseAccessTokenVerifier(supabase_url)

    token = env.get("AI_VASTU_DEV_BEARER_TOKEN", "dev-local-token")
    raw_user_id = env.get("AI_VASTU_DEV_USER_ID", str(_DEFAULT_DEV_USER_ID))
    try:
        user_id = UUID(raw_user_id)
    except ValueError as exc:
        raise AuthConfigurationError("AI_VASTU_DEV_USER_ID must be a UUID.") from exc
    return DevelopmentAccessTokenVerifier(token, user_id)
