from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

import httpx
from pydantic import ValidationError

from ai_vastu.provider_runtime import (
    ProviderFailureCategory,
    ProviderRuntimeError,
    read_limited_provider_response,
)

OLLAMA_LOCAL_PROVIDER = "ollama_local"
OLLAMA_LOCAL_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_LOCAL_MODEL = "qwen3-vl:8b-instruct-q4_K_M"

DEFAULT_CONNECT_TIMEOUT_SECONDS = 3.0
DEFAULT_READ_TIMEOUT_SECONDS = 300.0
DEFAULT_TOTAL_TIMEOUT_SECONDS = 360.0
DEFAULT_WRITE_TIMEOUT_SECONDS = 30.0
DEFAULT_POOL_TIMEOUT_SECONDS = 3.0

MAX_CONNECT_TIMEOUT_SECONDS = 10.0
MAX_READ_TIMEOUT_SECONDS = 300.0
MAX_TOTAL_TIMEOUT_SECONDS = 360.0
MAX_WRITE_TIMEOUT_SECONDS = 60.0
MAX_POOL_TIMEOUT_SECONDS = 10.0

# Large enough for bounded plan-page images while preventing unbounded base64 payloads.
MAX_OLLAMA_REQUEST_BYTES = 48 * 1024 * 1024
MAX_VALIDATION_ISSUES = 8
MAX_VALIDATION_LOCATION_DEPTH = 8

_SAFE_VALIDATION_LOCATION_FIELDS = frozenset(
    {
        "approximate_area_mm2",
        "built_up_area_mm2",
        "centroid_x_basis_points",
        "centroid_y_basis_points",
        "confidence",
        "content_hash",
        "depth_mm",
        "entrance_facing",
        "envelope",
        "evidence",
        "geometry_type",
        "intake_id",
        "label",
        "model",
        "north_rotation_deg",
        "observations",
        "orientation",
        "project_id",
        "provider",
        "questions",
        "reference_names",
        "requires_confirmation",
        "road_side",
        "room_type",
        "rooms",
        "schema_version",
        "source",
        "warnings",
        "width_mm",
    }
)
_SAFE_VALIDATION_ERROR_TYPES = frozenset(
    {
        "assertion_error",
        "bool_type",
        "enum",
        "extra_forbidden",
        "finite_number",
        "float_parsing",
        "float_type",
        "greater_than",
        "greater_than_equal",
        "int_parsing",
        "int_type",
        "less_than",
        "less_than_equal",
        "list_type",
        "literal_error",
        "missing",
        "model_type",
        "string_too_long",
        "string_type",
        "tuple_type",
        "uuid_parsing",
        "uuid_type",
        "value_error",
    }
)


class OllamaLocalFailureStage(StrEnum):
    PROVIDER_TRANSPORT_HTTP = "provider_transport_http"
    STRICT_JSON = "strict_json"
    APPLICATION_VALIDATION = "application_validation"
    PROVENANCE = "provenance"


class OllamaLocalTimeoutKind(StrEnum):
    CONNECT = "connect"
    READ = "read"
    WRITE = "write"
    POOL = "pool"
    TOTAL = "total"


class OllamaLocalConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OllamaLocalValidationIssue:
    location: str
    error_type: str


class OllamaLocalRequestError(ProviderRuntimeError):
    def __init__(
        self,
        category: ProviderFailureCategory,
        *,
        http_status: int | None = None,
        stage: OllamaLocalFailureStage = OllamaLocalFailureStage.PROVIDER_TRANSPORT_HTTP,
        validation_issues: tuple[OllamaLocalValidationIssue, ...] = (),
        timeout_kind: OllamaLocalTimeoutKind | None = None,
    ) -> None:
        self.http_status = (
            http_status if isinstance(http_status, int) and 100 <= http_status <= 599 else None
        )
        self.stage = stage
        self.model_id = (
            OLLAMA_LOCAL_MODEL
            if stage in {
                OllamaLocalFailureStage.STRICT_JSON,
                OllamaLocalFailureStage.APPLICATION_VALIDATION,
                OllamaLocalFailureStage.PROVENANCE,
            }
            else None
        )
        self.attempts = 1
        self.validation_issues = tuple(
            _sanitize_validation_issue(issue)
            for issue in validation_issues[:MAX_VALIDATION_ISSUES]
        )
        self.timeout_kind = (
            timeout_kind if category is ProviderFailureCategory.TIMEOUT else None
        )
        super().__init__(category, OLLAMA_LOCAL_PROVIDER)


T = TypeVar("T")


def _validation_location(value: object) -> str:
    if not isinstance(value, tuple):
        return "<root>"
    parts: list[str] = []
    for segment in value[:MAX_VALIDATION_LOCATION_DEPTH]:
        if isinstance(segment, int):
            parts.append(str(segment) if 0 <= segment <= 999 else "<index>")
        elif isinstance(segment, str) and segment in _SAFE_VALIDATION_LOCATION_FIELDS:
            parts.append(segment)
        else:
            parts.append("<field>")
    if len(value) > MAX_VALIDATION_LOCATION_DEPTH:
        parts.append("<depth>")
    return ".".join(parts) if parts else "<root>"


def _validation_issues(exc: ValidationError) -> tuple[OllamaLocalValidationIssue, ...]:
    issues: list[OllamaLocalValidationIssue] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    )[:MAX_VALIDATION_ISSUES]:
        raw_type = error.get("type")
        error_type = (
            raw_type
            if isinstance(raw_type, str) and raw_type in _SAFE_VALIDATION_ERROR_TYPES
            else "validation_error"
        )
        issues.append(
            OllamaLocalValidationIssue(
                location=_validation_location(error.get("loc")),
                error_type=error_type,
            )
        )
    return tuple(issues)


def _sanitize_validation_issue(value: object) -> OllamaLocalValidationIssue:
    if not isinstance(value, OllamaLocalValidationIssue):
        return OllamaLocalValidationIssue("<root>", "validation_error")

    raw_parts = value.location.split(".")
    parts: list[str] = []
    for segment in raw_parts[:MAX_VALIDATION_LOCATION_DEPTH]:
        if (
            segment in _SAFE_VALIDATION_LOCATION_FIELDS
            or segment in {"<root>", "<field>", "<depth>"}
            or (segment.isdecimal() and 0 <= int(segment) <= 999)
        ):
            parts.append(segment)
        else:
            parts.append("<field>")
    if len(raw_parts) > MAX_VALIDATION_LOCATION_DEPTH:
        parts.append("<depth>")
    location = ".".join(parts) if parts else "<root>"
    error_type = (
        value.error_type
        if value.error_type in _SAFE_VALIDATION_ERROR_TYPES
        else "validation_error"
    )
    return OllamaLocalValidationIssue(location, error_type)


def _finite_timeout(value: float, *, name: str, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OllamaLocalConfigurationError(f"{name} must be a finite positive number.")
    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0 or normalized > maximum:
        raise OllamaLocalConfigurationError(
            f"{name} must be finite, positive, and no greater than {maximum:g} seconds."
        )
    return normalized


def _environment_timeout(
    environment: Mapping[str, str],
    name: str,
    default: float,
    maximum: float,
) -> float:
    raw = environment.get(name)
    if raw is None:
        return default
    try:
        value = float(raw.strip())
    except ValueError:
        raise OllamaLocalConfigurationError(f"{name} must be a number.") from None
    return _finite_timeout(value, name=name, maximum=maximum)


def _status_category(status_code: int) -> ProviderFailureCategory:
    if status_code in {408, 504}:
        return ProviderFailureCategory.TIMEOUT
    if status_code == 429:
        return ProviderFailureCategory.RATE_LIMITED
    if status_code in {401, 403}:
        return ProviderFailureCategory.AUTHENTICATION
    if 400 <= status_code < 500:
        return ProviderFailureCategory.REQUEST_REJECTED
    return ProviderFailureCategory.UNAVAILABLE


def _transport_category(exc: httpx.TransportError) -> ProviderFailureCategory:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderFailureCategory.TIMEOUT
    return ProviderFailureCategory.UNAVAILABLE


def _transport_timeout_kind(
    exc: httpx.TransportError,
) -> OllamaLocalTimeoutKind | None:
    if isinstance(exc, httpx.ConnectTimeout):
        return OllamaLocalTimeoutKind.CONNECT
    if isinstance(exc, httpx.ReadTimeout):
        return OllamaLocalTimeoutKind.READ
    if isinstance(exc, httpx.WriteTimeout):
        return OllamaLocalTimeoutKind.WRITE
    if isinstance(exc, httpx.PoolTimeout):
        return OllamaLocalTimeoutKind.POOL
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
        raise ValueError("Ollama response was not strict JSON.") from None
    if not isinstance(parsed, dict):
        raise ValueError("Ollama structured output was not a JSON object.")
    return parsed


def _request_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise OllamaLocalConfigurationError("Ollama request payload is invalid.") from None
    if len(encoded) > MAX_OLLAMA_REQUEST_BYTES:
        raise OllamaLocalConfigurationError("Ollama request exceeds the configured size limit.")
    return encoded


class OllamaLocalClient:
    def __init__(
        self,
        *,
        base_url: str = OLLAMA_LOCAL_BASE_URL,
        model: str = OLLAMA_LOCAL_MODEL,
        connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
        total_timeout_seconds: float = DEFAULT_TOTAL_TIMEOUT_SECONDS,
        write_timeout_seconds: float = DEFAULT_WRITE_TIMEOUT_SECONDS,
        pool_timeout_seconds: float = DEFAULT_POOL_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if base_url.rstrip("/") != OLLAMA_LOCAL_BASE_URL:
            raise OllamaLocalConfigurationError(
                f"Ollama endpoint must remain pinned to {OLLAMA_LOCAL_BASE_URL}."
            )
        if model != OLLAMA_LOCAL_MODEL:
            raise OllamaLocalConfigurationError(
                f"Ollama model must remain pinned to {OLLAMA_LOCAL_MODEL!r}."
            )
        self._base_url = OLLAMA_LOCAL_BASE_URL
        self._model = OLLAMA_LOCAL_MODEL
        self._connect_timeout = _finite_timeout(
            connect_timeout_seconds,
            name="Ollama connect timeout",
            maximum=MAX_CONNECT_TIMEOUT_SECONDS,
        )
        self._read_timeout = _finite_timeout(
            read_timeout_seconds,
            name="Ollama read timeout",
            maximum=MAX_READ_TIMEOUT_SECONDS,
        )
        self._total_timeout = _finite_timeout(
            total_timeout_seconds,
            name="Ollama total timeout",
            maximum=MAX_TOTAL_TIMEOUT_SECONDS,
        )
        self._write_timeout = _finite_timeout(
            write_timeout_seconds,
            name="Ollama write timeout",
            maximum=MAX_WRITE_TIMEOUT_SECONDS,
        )
        self._pool_timeout = _finite_timeout(
            pool_timeout_seconds,
            name="Ollama pool timeout",
            maximum=MAX_POOL_TIMEOUT_SECONDS,
        )
        self._transport = transport
        self._monotonic = monotonic

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> OllamaLocalClient:
        source = os.environ if environment is None else environment
        if source.get("APP_ENV", "").strip().lower() != "development":
            raise OllamaLocalConfigurationError(
                "Local Ollama is available only with explicit APP_ENV=development."
            )
        if source.get("AI_VASTU_OLLAMA_FALLBACK_MODEL", "").strip():
            raise OllamaLocalConfigurationError("Ollama model fallback is not supported.")
        return cls(
            base_url=source.get("AI_VASTU_OLLAMA_BASE_URL", OLLAMA_LOCAL_BASE_URL).strip(),
            model=source.get("AI_VASTU_OLLAMA_MODEL", OLLAMA_LOCAL_MODEL).strip(),
            connect_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_OLLAMA_CONNECT_TIMEOUT_SECONDS",
                DEFAULT_CONNECT_TIMEOUT_SECONDS,
                MAX_CONNECT_TIMEOUT_SECONDS,
            ),
            read_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_OLLAMA_READ_TIMEOUT_SECONDS",
                DEFAULT_READ_TIMEOUT_SECONDS,
                MAX_READ_TIMEOUT_SECONDS,
            ),
            total_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_OLLAMA_TOTAL_TIMEOUT_SECONDS",
                DEFAULT_TOTAL_TIMEOUT_SECONDS,
                MAX_TOTAL_TIMEOUT_SECONDS,
            ),
            write_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_OLLAMA_WRITE_TIMEOUT_SECONDS",
                DEFAULT_WRITE_TIMEOUT_SECONDS,
                MAX_WRITE_TIMEOUT_SECONDS,
            ),
            pool_timeout_seconds=_environment_timeout(
                source,
                "AI_VASTU_OLLAMA_POOL_TIMEOUT_SECONDS",
                DEFAULT_POOL_TIMEOUT_SECONDS,
                MAX_POOL_TIMEOUT_SECONDS,
            ),
            transport=transport,
        )

    def _timeout(self, remaining: float) -> httpx.Timeout:
        bounded_remaining = max(0.001, remaining)
        return httpx.Timeout(
            connect=min(self._connect_timeout, bounded_remaining),
            read=min(self._read_timeout, bounded_remaining),
            write=min(self._write_timeout, bounded_remaining),
            pool=min(self._pool_timeout, bounded_remaining),
        )

    def _ensure_before_deadline(self, deadline: float) -> None:
        if self._monotonic() >= deadline:
            raise OllamaLocalRequestError(
                ProviderFailureCategory.TIMEOUT,
                timeout_kind=OllamaLocalTimeoutKind.TOTAL,
            )

    def _send(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        deadline: float | None = None,
    ) -> bytes:
        if deadline is None:
            deadline = self._monotonic() + self._total_timeout
        content = None if payload is None else _request_json_bytes(payload)
        headers = {"Accept-Encoding": "identity"}
        if content is not None:
            headers["Content-Type"] = "application/json"
        sanitized_transport_failure: tuple[
            ProviderFailureCategory,
            OllamaLocalTimeoutKind | None,
        ] | None = None
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
                    method,
                    path,
                    content=content,
                    timeout=self._timeout(remaining),
                ) as response:
                    self._ensure_before_deadline(deadline)
                    if not response.is_success:
                        raise OllamaLocalRequestError(
                            _status_category(response.status_code),
                            http_status=response.status_code,
                        )
                    return read_limited_provider_response(
                        response,
                        provider=OLLAMA_LOCAL_PROVIDER,
                        deadline=deadline,
                        monotonic=self._monotonic,
                    )
        except ProviderRuntimeError as exc:
            if isinstance(exc, OllamaLocalRequestError):
                raise
            sanitized_transport_failure = (
                exc.category,
                OllamaLocalTimeoutKind.TOTAL
                if exc.category is ProviderFailureCategory.TIMEOUT
                else None,
            )
        except httpx.TransportError as exc:
            sanitized_transport_failure = (
                _transport_category(exc),
                _transport_timeout_kind(exc),
            )
        if sanitized_transport_failure is None:
            raise OllamaLocalRequestError(ProviderFailureCategory.UNAVAILABLE)
        category, timeout_kind = sanitized_transport_failure
        raise OllamaLocalRequestError(category, timeout_kind=timeout_kind)

    def complete_validated_json(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        schema: Mapping[str, Any],
        validator: Callable[[dict[str, Any], str], T],
        max_tokens: int | None = None,
    ) -> T:
        if isinstance(messages, (str, bytes)) or not isinstance(messages, Sequence):
            raise OllamaLocalConfigurationError("Ollama messages must be a sequence.")
        if not isinstance(schema, Mapping):
            raise OllamaLocalConfigurationError("Ollama format schema must be an object.")
        if max_tokens is not None and (
            isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0
        ):
            raise OllamaLocalConfigurationError("Ollama max_tokens must be a positive integer.")

        options: dict[str, Any] = {"temperature": 0}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        body: dict[str, Any] = {
            "model": self._model,
            "messages": list(messages),
            "stream": False,
            "format": dict(schema),
            "options": options,
        }
        deadline = self._monotonic() + self._total_timeout
        response_bytes = self._send("POST", "/api/chat", payload=body, deadline=deadline)
        try:
            response = _strict_json_object(response_bytes)
            self._ensure_before_deadline(deadline)
            if response.get("model") != self._model or response.get("done") is not True:
                raise OllamaLocalRequestError(
                    ProviderFailureCategory.INVALID_RESPONSE,
                    stage=OllamaLocalFailureStage.PROVENANCE,
                )
            message = response.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError("Ollama response message was malformed.")
            parsed = _strict_json_object(message["content"])
            self._ensure_before_deadline(deadline)
        except OllamaLocalRequestError:
            raise
        except (TypeError, ValueError, KeyError):
            raise OllamaLocalRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=OllamaLocalFailureStage.STRICT_JSON,
            ) from None
        validation_issues: tuple[OllamaLocalValidationIssue, ...] = ()
        validation_failed = False
        try:
            validated = validator(parsed, self._model)
        except ValidationError as exc:
            validation_issues = _validation_issues(exc)
            validation_failed = True
        except Exception:
            validation_failed = True
        if validation_failed:
            raise OllamaLocalRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=OllamaLocalFailureStage.APPLICATION_VALIDATION,
                validation_issues=validation_issues,
            )
        self._ensure_before_deadline(deadline)
        return validated

    def verify_endpoint(self) -> str:
        response_bytes = self._send("GET", "/api/version")
        try:
            payload = _strict_json_object(response_bytes)
            version = payload.get("version")
            if not isinstance(version, str) or not version.strip():
                raise ValueError
        except (TypeError, ValueError, KeyError):
            raise OllamaLocalRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=OllamaLocalFailureStage.STRICT_JSON,
            ) from None
        return version

    def verify_pinned_model_available(self) -> str:
        response_bytes = self._send("GET", "/api/tags")
        try:
            payload = _strict_json_object(response_bytes)
            models = payload.get("models")
            if not isinstance(models, list):
                raise ValueError
            pinned_model_available = False
            for item in models:
                if not isinstance(item, dict):
                    raise ValueError
                identities = [item[key] for key in ("name", "model") if key in item]
                if not identities or not all(isinstance(value, str) for value in identities):
                    raise ValueError
                if self._model in identities and any(
                    value != self._model for value in identities
                ):
                    raise OllamaLocalRequestError(
                        ProviderFailureCategory.INVALID_RESPONSE,
                        stage=OllamaLocalFailureStage.PROVENANCE,
                    )
                if all(value == self._model for value in identities):
                    pinned_model_available = True
        except (TypeError, ValueError, KeyError):
            raise OllamaLocalRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=OllamaLocalFailureStage.STRICT_JSON,
            ) from None
        if not pinned_model_available:
            raise OllamaLocalRequestError(
                ProviderFailureCategory.INVALID_RESPONSE,
                stage=OllamaLocalFailureStage.PROVENANCE,
            )
        return self._model
