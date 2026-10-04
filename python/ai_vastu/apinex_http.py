from __future__ import annotations

import base64
import binascii
import json
import math
import os
import time
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from typing import Any, TypeVar, cast

import httpx

from ai_vastu.provider_runtime import (
    MAX_PROVIDER_RESPONSE_BYTES,
    ProviderFailureCategory,
    ProviderRuntimeError,
    read_limited_provider_response,
)

APINEX_PROVIDER = "apinex"
APINEX_API_BASE = "https://api.apinex.bond/v1"
APINEX_MODEL = "free/gpt-6-luna"

DEFAULT_CONNECT_TIMEOUT_SECONDS = 5.0
DEFAULT_READ_TIMEOUT_SECONDS = 180.0
DEFAULT_TOTAL_TIMEOUT_SECONDS = 240.0
DEFAULT_WRITE_TIMEOUT_SECONDS = 30.0
DEFAULT_POOL_TIMEOUT_SECONDS = 5.0

MAX_CONNECT_TIMEOUT_SECONDS = 15.0
MAX_READ_TIMEOUT_SECONDS = 300.0
MAX_TOTAL_TIMEOUT_SECONDS = 360.0
MAX_WRITE_TIMEOUT_SECONDS = 60.0
MAX_POOL_TIMEOUT_SECONDS = 15.0
MAX_APINEX_REQUEST_BYTES = 48 * 1024 * 1024


class ApinexFailureStage(StrEnum):
    MODEL_INVENTORY = "model_inventory"
    PROVIDER_TRANSPORT_HTTP = "provider_transport_http"
    RESPONSE_ENVELOPE = "response_envelope"
    STRICT_JSON = "strict_json"
    APPLICATION_VALIDATION = "application_validation"
    PROVENANCE = "provenance"
    CONTENT_HASH = "content_hash"


class ApinexTimeoutKind(StrEnum):
    CONNECT = "connect"
    READ = "read"
    WRITE = "write"
    POOL = "pool"
    TOTAL = "total"


class ApinexConfigurationError(RuntimeError):
    pass


class ApinexRequestError(ProviderRuntimeError):
    def __init__(
        self,
        category: ProviderFailureCategory,
        *,
        http_status: int | None = None,
        stage: ApinexFailureStage = ApinexFailureStage.PROVIDER_TRANSPORT_HTTP,
        timeout_kind: ApinexTimeoutKind | None = None,
    ) -> None:
        self.http_status = (
            http_status if isinstance(http_status, int) and 100 <= http_status <= 599 else None
        )
        self.stage = stage
        self.model_id = APINEX_MODEL if stage is not ApinexFailureStage.MODEL_INVENTORY else None
        self.attempts = 1
        self.timeout_kind = timeout_kind if category is ProviderFailureCategory.TIMEOUT else None
        super().__init__(category, APINEX_PROVIDER)


T = TypeVar("T")


def _finite_timeout(value: float, *, name: str, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApinexConfigurationError(f"{name} must be a finite positive number.")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0 or normalized > maximum:
        raise ApinexConfigurationError(
            f"{name} must be finite, positive, and no greater than {maximum:g} seconds."
        )
    return normalized


def _environment_timeout(
    environment: Mapping[str, str], name: str, default: float, maximum: float
) -> float:
    raw = environment.get(name)
    if raw is None:
        return default
    try:
        value = float(raw.strip())
    except ValueError:
        raise ApinexConfigurationError(f"{name} must be a number.") from None
    return _finite_timeout(value, name=name, maximum=maximum)


def _status_category(status_code: int) -> ProviderFailureCategory:
    if status_code in {401, 403}:
        return ProviderFailureCategory.AUTHENTICATION
    if status_code in {408, 504}:
        return ProviderFailureCategory.TIMEOUT
    if status_code == 429:
        return ProviderFailureCategory.RATE_LIMITED
    if 400 <= status_code < 500:
        return ProviderFailureCategory.REQUEST_REJECTED
    return ProviderFailureCategory.UNAVAILABLE


def _transport_category(exc: httpx.TransportError) -> ProviderFailureCategory:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderFailureCategory.TIMEOUT
    return ProviderFailureCategory.UNAVAILABLE


def _timeout_kind(exc: httpx.TransportError) -> ApinexTimeoutKind | None:
    if isinstance(exc, httpx.ConnectTimeout):
        return ApinexTimeoutKind.CONNECT
    if isinstance(exc, httpx.ReadTimeout):
        return ApinexTimeoutKind.READ
    if isinstance(exc, httpx.WriteTimeout):
        return ApinexTimeoutKind.WRITE
    if isinstance(exc, httpx.PoolTimeout):
        return ApinexTimeoutKind.POOL
    return None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key.")
        result[key] = value
    return result


def _reject_non_finite_constant(_value: str) -> None:
    raise ValueError("Non-finite JSON number.")


def _strict_json_object(value: bytes | str) -> dict[str, Any]:
    try:
        text = value.decode("utf-8") if isinstance(value, bytes) else value
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
        raise ValueError("APINEX response was not strict JSON.") from None
    if not isinstance(parsed, dict):
        raise ValueError("APINEX structured output was not a JSON object.")
    return parsed


def _request_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ApinexConfigurationError("APINEX request payload is invalid.") from None
    if len(encoded) > MAX_APINEX_REQUEST_BYTES:
        raise ApinexConfigurationError("APINEX request exceeds the configured size limit.")
    return encoded


def image_url_part(content_type: str, data: bytes) -> dict[str, Any]:
    if content_type not in {"image/png", "image/jpeg"}:
        raise ApinexConfigurationError("APINEX image media type is unsupported.")
    encoded = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{content_type};base64,{encoded}"},
    }


def strict_schema_response_format(schema: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, Mapping):
        raise ApinexConfigurationError("APINEX structured-output schema must be an object.")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "vastudraw_contract",
            "strict": True,
            "schema": dict(schema),
        },
    }


RAW_JSON_INSTRUCTION = (
    "Return raw JSON only. Match the supplied schema exactly. Do not use Markdown "
    "or code fences. Do not include prose outside JSON. Do not add extra keys."
)


def _openai_messages(messages: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise ApinexConfigurationError("APINEX message was invalid.")
        role = message.get("role")
        content = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise ApinexConfigurationError("APINEX message was invalid.")
        if index == 0 and role == "system":
            content = f"{content.rstrip()}\n\n{RAW_JSON_INSTRUCTION}"
        images = message.get("images")
        if images is None:
            prepared.append({"role": role, "content": content})
            continue
        if role != "user" or not isinstance(images, list):
            raise ApinexConfigurationError("APINEX image message was invalid.")
        parts: list[dict[str, Any]] = [{"type": "text", "text": content}]
        for encoded in images:
            if not isinstance(encoded, str):
                raise ApinexConfigurationError("APINEX image message was invalid.")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                raise ApinexConfigurationError("APINEX image message was invalid.") from None
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                content_type = "image/png"
            elif data.startswith(b"\xff\xd8\xff"):
                content_type = "image/jpeg"
            else:
                raise ApinexConfigurationError("APINEX image message was invalid.")
            parts.append(image_url_part(content_type, data))
        prepared.append({"role": role, "content": parts})
    if not prepared or prepared[0]["role"] != "system":
        prepared.insert(0, {"role": "system", "content": RAW_JSON_INSTRUCTION})
    return prepared


class ApinexClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = APINEX_API_BASE,
        model: str = APINEX_MODEL,
        connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
        total_timeout_seconds: float = DEFAULT_TOTAL_TIMEOUT_SECONDS,
        write_timeout_seconds: float = DEFAULT_WRITE_TIMEOUT_SECONDS,
        pool_timeout_seconds: float = DEFAULT_POOL_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not api_key.strip():
            raise ApinexConfigurationError("APINEX_API_KEY is required.")
        if base_url.rstrip("/") != APINEX_API_BASE:
            raise ApinexConfigurationError(
                f"APINEX endpoint must remain pinned to {APINEX_API_BASE}."
            )
        if model != APINEX_MODEL:
            raise ApinexConfigurationError(f"APINEX model must remain pinned to {APINEX_MODEL!r}.")
        self._api_key = api_key.strip()
        self._base_url = APINEX_API_BASE
        self._model = APINEX_MODEL
        self._connect_timeout = _finite_timeout(
            connect_timeout_seconds,
            name="APINEX connect timeout",
            maximum=MAX_CONNECT_TIMEOUT_SECONDS,
        )
        self._read_timeout = _finite_timeout(
            read_timeout_seconds, name="APINEX read timeout", maximum=MAX_READ_TIMEOUT_SECONDS
        )
        self._total_timeout = _finite_timeout(
            total_timeout_seconds, name="APINEX total timeout", maximum=MAX_TOTAL_TIMEOUT_SECONDS
        )
        self._write_timeout = _finite_timeout(
            write_timeout_seconds, name="APINEX write timeout", maximum=MAX_WRITE_TIMEOUT_SECONDS
        )
        self._pool_timeout = _finite_timeout(
            pool_timeout_seconds, name="APINEX pool timeout", maximum=MAX_POOL_TIMEOUT_SECONDS
        )
        self._transport = transport
        self._monotonic = monotonic

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> ApinexClient:
        source = os.environ if environment is None else environment
        if source.get("APP_ENV", "").strip().lower() != "development":
            raise ApinexConfigurationError(
                "APINEX is available only with explicit APP_ENV=development."
            )
        if source.get("AI_VASTU_APINEX_FALLBACK_MODEL", "").strip():
            raise ApinexConfigurationError("APINEX model fallback is not supported.")
        return cls(
            api_key=source.get("APINEX_API_KEY", ""),
            base_url=source.get("AI_VASTU_APINEX_BASE_URL", APINEX_API_BASE).strip(),
            model=source.get("AI_VASTU_APINEX_MODEL", APINEX_MODEL).strip(),
            connect_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_APINEX_CONNECT_TIMEOUT_SECONDS",
                DEFAULT_CONNECT_TIMEOUT_SECONDS,
                MAX_CONNECT_TIMEOUT_SECONDS,
            ),
            read_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_APINEX_READ_TIMEOUT_SECONDS",
                DEFAULT_READ_TIMEOUT_SECONDS,
                MAX_READ_TIMEOUT_SECONDS,
            ),
            total_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_APINEX_TOTAL_TIMEOUT_SECONDS",
                DEFAULT_TOTAL_TIMEOUT_SECONDS,
                MAX_TOTAL_TIMEOUT_SECONDS,
            ),
            write_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_APINEX_WRITE_TIMEOUT_SECONDS",
                DEFAULT_WRITE_TIMEOUT_SECONDS,
                MAX_WRITE_TIMEOUT_SECONDS,
            ),
            pool_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_APINEX_POOL_TIMEOUT_SECONDS",
                DEFAULT_POOL_TIMEOUT_SECONDS,
                MAX_POOL_TIMEOUT_SECONDS,
            ),
            transport=transport,
        )

    def _timeout(self, remaining: float) -> httpx.Timeout:
        bounded = max(0.001, remaining)
        return httpx.Timeout(
            connect=min(self._connect_timeout, bounded),
            read=min(self._read_timeout, bounded),
            write=min(self._write_timeout, bounded),
            pool=min(self._pool_timeout, bounded),
        )

    def _ensure_before_deadline(self, deadline: float) -> None:
        if self._monotonic() >= deadline:
            raise ApinexRequestError(
                ProviderFailureCategory.TIMEOUT,
                timeout_kind=ApinexTimeoutKind.TOTAL,
            )

    def _send(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        deadline: float | None = None,
        stage: ApinexFailureStage = ApinexFailureStage.PROVIDER_TRANSPORT_HTTP,
    ) -> bytes:
        if deadline is None:
            deadline = self._monotonic() + self._total_timeout
        content = None if payload is None else _request_json_bytes(payload)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept-Encoding": "identity",
        }
        if content is not None:
            headers["Content-Type"] = "application/json"
        failure: tuple[ProviderFailureCategory, ApinexTimeoutKind | None] | None = None
        try:
            with httpx.Client(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout(self._total_timeout),
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                remaining = deadline - self._monotonic()
                self._ensure_before_deadline(deadline)
                with client.stream(
                    method, path, content=content, timeout=self._timeout(remaining)
                ) as response:
                    self._ensure_before_deadline(deadline)
                    if not response.is_success:
                        raise ApinexRequestError(
                            _status_category(response.status_code),
                            http_status=response.status_code,
                            stage=stage,
                        )
                    return read_limited_provider_response(
                        response,
                        provider=APINEX_PROVIDER,
                        max_bytes=MAX_PROVIDER_RESPONSE_BYTES,
                        deadline=deadline,
                        monotonic=self._monotonic,
                    )
        except ApinexRequestError:
            raise
        except ProviderRuntimeError as exc:
            failure = (
                exc.category,
                ApinexTimeoutKind.TOTAL
                if exc.category is ProviderFailureCategory.TIMEOUT
                else None,
            )
        except httpx.TransportError as exc:
            failure = (_transport_category(exc), _timeout_kind(exc))
        if failure is None:
            raise ApinexRequestError(ProviderFailureCategory.UNAVAILABLE, stage=stage)
        category, timeout_kind = failure
        raise ApinexRequestError(category, stage=stage, timeout_kind=timeout_kind) from None

    def verify_pinned_model_available(self) -> str:
        raw = self._send("GET", "/models", stage=ApinexFailureStage.MODEL_INVENTORY)
        try:
            payload = _strict_json_object(raw)
            data = payload.get("data")
            if not isinstance(data, list):
                raise ValueError
            model_ids: set[str] = set()
            for item in data:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    raise ValueError
                model_ids.add(item["id"])
        except (TypeError, ValueError, KeyError):
            raise ApinexRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=ApinexFailureStage.MODEL_INVENTORY,
            ) from None
        if self._model not in model_ids:
            raise ApinexRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=ApinexFailureStage.MODEL_INVENTORY,
            )
        return self._model

    def verify_endpoint(self) -> str:
        raw = self._send("GET", "/models", stage=ApinexFailureStage.MODEL_INVENTORY)
        try:
            payload = _strict_json_object(raw)
            if not isinstance(payload.get("data"), list):
                raise ValueError
        except (TypeError, ValueError, KeyError):
            raise ApinexRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=ApinexFailureStage.MODEL_INVENTORY,
            ) from None
        return APINEX_API_BASE

    def complete_text(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        max_tokens: int | None = None,
    ) -> str:
        if isinstance(messages, (str, bytes)) or not isinstance(messages, Sequence):
            raise ApinexConfigurationError("APINEX messages must be a sequence.")
        plain_messages: list[dict[str, str]] = []
        for message in messages:
            if not isinstance(message, dict):
                raise ApinexConfigurationError("APINEX message was invalid.")
            role = message.get("role")
            content = message.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(content, str):
                raise ApinexConfigurationError("APINEX message was invalid.")
            plain_messages.append({"role": role, "content": content})
        body: dict[str, Any] = {
            "model": self._model,
            "messages": plain_messages,
            "temperature": 0,
            "stream": False,
        }
        if max_tokens is not None:
            if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
                raise ApinexConfigurationError("APINEX max_tokens must be a positive integer.")
            body["max_tokens"] = max_tokens
        deadline = self._monotonic() + self._total_timeout
        raw = self._send("POST", "/chat/completions", payload=body, deadline=deadline)
        try:
            envelope = _strict_json_object(raw)
            if envelope.get("model") != self._model:
                raise ApinexRequestError(
                    ProviderFailureCategory.INVALID_RESPONSE,
                    stage=ApinexFailureStage.PROVENANCE,
                )
            choices = envelope.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError
            message = choices[0].get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError
            content = message["content"]
        except ApinexRequestError:
            raise
        except (AttributeError, TypeError, ValueError, KeyError, IndexError):
            raise ApinexRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=ApinexFailureStage.RESPONSE_ENVELOPE,
            ) from None
        self._ensure_before_deadline(deadline)
        return cast(str, content)

    def complete_validated_json(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        schema: Mapping[str, Any],
        validator: Callable[[dict[str, Any], str], T],
        max_tokens: int | None = None,
    ) -> T:
        if isinstance(messages, (str, bytes)) or not isinstance(messages, Sequence):
            raise ApinexConfigurationError("APINEX messages must be a sequence.")
        if max_tokens is not None and (
            isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0
        ):
            raise ApinexConfigurationError("APINEX max_tokens must be a positive integer.")
        body: dict[str, Any] = {
            "model": self._model,
            "messages": _openai_messages(messages),
            "temperature": 0,
            "stream": False,
            "response_format": strict_schema_response_format(schema),
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        deadline = self._monotonic() + self._total_timeout
        raw = self._send("POST", "/chat/completions", payload=body, deadline=deadline)
        try:
            envelope = _strict_json_object(raw)
            if envelope.get("model") != self._model:
                raise ApinexRequestError(
                    ProviderFailureCategory.INVALID_RESPONSE,
                    stage=ApinexFailureStage.PROVENANCE,
                )
            choices = envelope.get("choices")
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError
            choice = choices[0]
            if not isinstance(choice, dict):
                raise ValueError
            message = choice.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError
            parsed = _strict_json_object(message["content"])
            self._ensure_before_deadline(deadline)
        except ApinexRequestError:
            raise
        except (TypeError, ValueError, KeyError):
            raise ApinexRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=ApinexFailureStage.STRICT_JSON,
            ) from None
        validation_failed = False
        try:
            validated = validator(parsed, self._model)
        except Exception:
            validation_failed = True
        if validation_failed:
            raise ApinexRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=ApinexFailureStage.APPLICATION_VALIDATION,
            ) from None
        self._ensure_before_deadline(deadline)
        return validated
