from __future__ import annotations

import math
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum

import httpx

MAX_PROVIDER_RESPONSE_BYTES = 2 * 1024 * 1024


class ProviderFailureCategory(StrEnum):
    AUTHENTICATION = "authentication"
    REQUEST_REJECTED = "request_rejected"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"


class ProviderRuntimeError(RuntimeError):
    """A provider failure safe to pass through internal error boundaries."""

    def __init__(
        self,
        category: ProviderFailureCategory,
        provider: str,
    ) -> None:
        normalized_provider = provider.strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", normalized_provider) is None:
            normalized_provider = "provider"
        self.category = category
        self.provider = normalized_provider
        super().__init__(
            f"{normalized_provider} request failed ({category.value})."
        )


class ProviderBudgetConfigurationError(ValueError):
    pass


def read_limited_provider_response(
    response: httpx.Response,
    *,
    provider: str,
    max_bytes: int = MAX_PROVIDER_RESPONSE_BYTES,
    deadline: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> bytes:
    """Read an untrusted provider response without buffering past the cap."""

    raw_length = response.headers.get("Content-Length")
    if raw_length is not None:
        try:
            declared_length = int(raw_length)
        except ValueError:
            raise ProviderRuntimeError(
                ProviderFailureCategory.INVALID_RESPONSE,
                provider,
            ) from None
        if declared_length < 0 or declared_length > max_bytes:
            raise ProviderRuntimeError(
                ProviderFailureCategory.INVALID_RESPONSE,
                provider,
            )

    content = bytearray()
    try:
        for chunk in response.iter_bytes():
            if deadline is not None and monotonic() >= deadline:
                raise ProviderRuntimeError(
                    ProviderFailureCategory.TIMEOUT,
                    provider,
                )
            if len(content) + len(chunk) > max_bytes:
                raise ProviderRuntimeError(
                    ProviderFailureCategory.INVALID_RESPONSE,
                    provider,
                )
            content.extend(chunk)
    except httpx.DecodingError:
        raise ProviderRuntimeError(
            ProviderFailureCategory.INVALID_RESPONSE,
            provider,
        ) from None
    if deadline is not None and monotonic() >= deadline:
        raise ProviderRuntimeError(
            ProviderFailureCategory.TIMEOUT,
            provider,
        )
    return bytes(content)


@dataclass(frozen=True, slots=True)
class ProviderBudget:
    attempt_timeout_seconds: float
    total_timeout_seconds: float
    retry_delay_seconds: float = 1.0
    max_retry_after_seconds: float = 5.0

    def __post_init__(self) -> None:
        values = {
            "attempt_timeout_seconds": self.attempt_timeout_seconds,
            "total_timeout_seconds": self.total_timeout_seconds,
            "retry_delay_seconds": self.retry_delay_seconds,
            "max_retry_after_seconds": self.max_retry_after_seconds,
        }
        for name, value in values.items():
            if not math.isfinite(value):
                raise ProviderBudgetConfigurationError(f"{name} must be finite.")
        if self.attempt_timeout_seconds <= 0:
            raise ProviderBudgetConfigurationError(
                "attempt_timeout_seconds must be greater than zero."
            )
        if self.total_timeout_seconds <= 0:
            raise ProviderBudgetConfigurationError(
                "total_timeout_seconds must be greater than zero."
            )
        if self.total_timeout_seconds < self.attempt_timeout_seconds:
            raise ProviderBudgetConfigurationError(
                "total_timeout_seconds must be at least attempt_timeout_seconds."
            )
        if self.retry_delay_seconds < 0:
            raise ProviderBudgetConfigurationError(
                "retry_delay_seconds must not be negative."
            )
        if self.max_retry_after_seconds < 0:
            raise ProviderBudgetConfigurationError(
                "max_retry_after_seconds must not be negative."
            )


DEFAULT_OPENROUTER_BUDGET = ProviderBudget(
    attempt_timeout_seconds=120.0,
    total_timeout_seconds=240.0,
    retry_delay_seconds=0.0,
    max_retry_after_seconds=0.0,
)

DEFAULT_GEMINI_BUDGET = ProviderBudget(
    attempt_timeout_seconds=90.0,
    total_timeout_seconds=181.0,
    retry_delay_seconds=1.0,
    max_retry_after_seconds=5.0,
)

DEFAULT_NVIDIA_NIM_BUDGET = ProviderBudget(
    attempt_timeout_seconds=120.0,
    total_timeout_seconds=240.0,
    retry_delay_seconds=0.0,
    max_retry_after_seconds=0.0,
)


def _environment_float(
    environment: Mapping[str, str],
    name: str,
    default: float,
) -> float:
    raw = environment.get(name)
    if raw is None:
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ProviderBudgetConfigurationError(f"{name} must be a number.") from exc


def load_provider_budget(
    environment: Mapping[str, str],
    *,
    prefix: str,
    default: ProviderBudget,
) -> ProviderBudget:
    """Load one provider's bounded runtime budget from an explicit environment."""

    if re.fullmatch(r"[A-Z][A-Z0-9_]*", prefix) is None:
        raise ProviderBudgetConfigurationError(
            "Provider budget prefix must contain uppercase environment-name characters."
        )
    return ProviderBudget(
        attempt_timeout_seconds=_environment_float(
            environment,
            f"{prefix}_ATTEMPT_TIMEOUT_SECONDS",
            default.attempt_timeout_seconds,
        ),
        total_timeout_seconds=_environment_float(
            environment,
            f"{prefix}_TOTAL_TIMEOUT_SECONDS",
            default.total_timeout_seconds,
        ),
        retry_delay_seconds=_environment_float(
            environment,
            f"{prefix}_RETRY_DELAY_SECONDS",
            default.retry_delay_seconds,
        ),
        max_retry_after_seconds=_environment_float(
            environment,
            f"{prefix}_MAX_RETRY_AFTER_SECONDS",
            default.max_retry_after_seconds,
        ),
    )
