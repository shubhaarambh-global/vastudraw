from __future__ import annotations

import json
import logging
import os
import time
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .rate_limit import consume_postgres_fixed_window, hash_rate_limit_key
from .settings import ProductionConfigurationError, load_production_settings

logger = logging.getLogger("ai_vastu.production")


class ProductionHardeningMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @staticmethod
    def _scope_for_path(path: str) -> str | None:
        if path == "/requirements/interpret":
            return "requirements_interpret"
        if path.startswith("/confirmed-generation/projects/"):
            return "confirmed_generation"
        if path == "/billing/checkout":
            return "billing_checkout"
        return None

    @staticmethod
    def _rate_key(request: Request) -> str:
        authorization = request.headers.get("authorization", "").strip()
        if authorization:
            return f"auth:{authorization}"
        host = request.client.host if request.client is not None else "unknown"
        return f"ip:{host}"

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = request.headers.get("x-request-id", "").strip() or str(uuid4())
        started = time.perf_counter()

        app_env = os.getenv("APP_ENV", "development").strip().lower()
        if app_env == "production":
            try:
                settings = load_production_settings()
            except ProductionConfigurationError as exc:
                response = JSONResponse(
                    {"detail": "Production configuration is invalid."},
                    status_code=503,
                )
                response.headers["X-Request-ID"] = request_id
                await response(scope, receive, send)
                logger.error(
                    json.dumps(
                        {
                            "event": "production_configuration_invalid",
                            "request_id": request_id,
                            "detail": str(exc),
                        }
                    )
                )
                return

            rate_scope = self._scope_for_path(request.url.path)
            if rate_scope is not None:
                limits = {
                    "requirements_interpret": settings.rate_limit_interpret_per_hour,
                    "confirmed_generation": settings.rate_limit_generation_per_hour,
                    "billing_checkout": settings.rate_limit_checkout_per_hour,
                }
                try:
                    decision = consume_postgres_fixed_window(
                        database_url=settings.database_url,
                        scope=rate_scope,
                        key_hash=hash_rate_limit_key(self._rate_key(request)),
                        limit=limits[rate_scope],
                    )
                except Exception:
                    logger.exception(
                        "Production rate limiter failed closed.",
                        extra={"request_id": request_id},
                    )
                    response = JSONResponse(
                        {"detail": "Rate-limit service unavailable."},
                        status_code=503,
                    )
                    response.headers["X-Request-ID"] = request_id
                    await response(scope, receive, send)
                    return
                if not decision.allowed:
                    response = JSONResponse(
                        {"detail": "Rate limit exceeded."},
                        status_code=429,
                    )
                    response.headers["Retry-After"] = "3600"
                    response.headers["X-Request-ID"] = request_id
                    await response(scope, receive, send)
                    return

        async def send_with_headers(message: Message) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-request-id", request_id.encode("ascii")),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (
                            b"permissions-policy",
                            b"camera=(), microphone=(), geolocation=()",
                        ),
                        (
                            b"content-security-policy",
                            b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
                        ),
                    ]
                )
                if app_env == "production":
                    hsts = str(load_production_settings().hsts_seconds).encode("ascii")
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=" + hsts + b"; includeSubDomains",
                        )
                    )
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "elapsed_ms": elapsed_ms,
                    },
                    separators=(",", ":"),
                )
            )
