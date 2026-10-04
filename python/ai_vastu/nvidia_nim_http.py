from __future__ import annotations

import base64
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

import httpx

from ai_vastu.provider_runtime import (
    DEFAULT_NVIDIA_NIM_BUDGET,
    ProviderBudget,
    ProviderBudgetConfigurationError,
    ProviderFailureCategory,
    ProviderRuntimeError,
    load_provider_budget,
    read_limited_provider_response,
)

NVIDIA_NIM_PROVIDER = "nvidia_nim"
NVIDIA_NIM_API_BASE = "https://integrate.api.nvidia.com/v1"

PRIMARY_TEXT_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
INACTIVE_UNQUALIFIED_TEXT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
VISION_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

PRIMARY_REASONING_MODEL = PRIMARY_TEXT_MODEL
VISION_PLAN_MODEL = VISION_MODEL

APPROVED_NVIDIA_NIM_MODELS = frozenset({PRIMARY_TEXT_MODEL, VISION_MODEL})


class NvidiaNimFailureStage(StrEnum):
    PROVIDER_TRANSPORT_HTTP = "provider_transport_http"
    STRICT_JSON = "strict_json"
    APPLICATION_VALIDATION = "application_validation"
    PROVENANCE = "provenance"
    FINAL_QUALIFICATION_ASSERTION = "final_qualification_assertion"

T = TypeVar("T")


class NvidiaNimConfigurationError(RuntimeError):
    pass


class NvidiaNimRequestError(ProviderRuntimeError):
    def __init__(
        self,
        category: ProviderFailureCategory,
        *,
        http_status: int | None = None,
        stage: NvidiaNimFailureStage = NvidiaNimFailureStage.PROVIDER_TRANSPORT_HTTP,
        model_id: str | None = None,
        attempts: int = 1,
    ) -> None:
        self.http_status = (
            http_status if isinstance(http_status, int) and 100 <= http_status <= 599 else None
        )
        self.stage = stage
        self.model_id = model_id if model_id in APPROVED_NVIDIA_NIM_MODELS else None
        self.attempts = attempts if attempts in {1, 2} else 1
        super().__init__(category, NVIDIA_NIM_PROVIDER)


@dataclass(frozen=True, slots=True)
class NvidiaNimModelPolicy:
    primary: str = PRIMARY_TEXT_MODEL
    vision: str = VISION_MODEL

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> NvidiaNimModelPolicy:
        source = os.environ if environment is None else environment
        if source.get("AI_VASTU_NVIDIA_FALLBACK_MODEL", "").strip():
            raise NvidiaNimConfigurationError(
                "AI_VASTU_NVIDIA_FALLBACK_MODEL is inactive and must not be configured."
            )
        policy = cls(
            primary=source.get(
                "AI_VASTU_NVIDIA_PRIMARY_MODEL",
                PRIMARY_TEXT_MODEL,
            ).strip(),
            vision=source.get(
                "AI_VASTU_NVIDIA_VISION_MODEL",
                VISION_MODEL,
            ).strip(),
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        expected = {
            "primary": PRIMARY_TEXT_MODEL,
            "vision": VISION_MODEL,
        }
        for role, expected_model in expected.items():
            if getattr(self, role) != expected_model:
                raise NvidiaNimConfigurationError(
                    f"{role} NVIDIA NIM model must remain pinned to {expected_model!r}."
                )

    @property
    def text_chain(self) -> tuple[str, ...]:
        return (self.primary,)

    @property
    def vision_chain(self) -> tuple[str, ...]:
        return (self.vision,)


def _approved_chain(models: Sequence[str]) -> tuple[str, ...]:
    chain = tuple(models)
    approved_chains = {
        (PRIMARY_TEXT_MODEL,),
        (VISION_MODEL,),
    }
    if chain not in approved_chains:
        raise NvidiaNimConfigurationError(
            "NVIDIA NIM model attempts must use an exact approved pinned chain."
        )
    return chain


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


def _eligible_transport_failure(exc: httpx.TransportError) -> bool:
    return isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
            httpx.ProxyError,
        ),
    )


def image_url_part(content_type: str, data: bytes) -> dict[str, Any]:
    if content_type not in {"image/png", "image/jpeg"}:
        raise ValueError(f"Unsupported NVIDIA NIM image media type: {content_type}.")
    encoded = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {"url": f"data:{content_type};base64,{encoded}"},
    }


def _strict_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text.strip())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("NVIDIA NIM response was not strict JSON.") from None
    if not isinstance(parsed, dict):
        raise ValueError("NVIDIA NIM structured output was not a JSON object.")
    return parsed


def _message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("NVIDIA NIM response did not contain choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("NVIDIA NIM response choice was malformed.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("NVIDIA NIM response did not contain a message.")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("NVIDIA NIM response did not contain text content.")
    return content


def _validated_response_format(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    copied = dict(value)
    if copied != {"type": "json_object"}:
        raise NvidiaNimConfigurationError(
            "NVIDIA NIM response_format must be the supported json_object form."
        )
    return copied


class NvidiaNimClient:
    def __init__(
        self,
        *,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        base_url: str = NVIDIA_NIM_API_BASE,
        budget: ProviderBudget = DEFAULT_NVIDIA_NIM_BUDGET,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not api_key.strip():
            raise NvidiaNimConfigurationError("NVIDIA_API_KEY is required.")
        if base_url.rstrip("/") != NVIDIA_NIM_API_BASE:
            raise NvidiaNimConfigurationError(
                "NVIDIA NIM runtime base URL is pinned to https://integrate.api.nvidia.com/v1."
            )
        if not isinstance(budget, ProviderBudget):
            raise NvidiaNimConfigurationError("NVIDIA NIM runtime budget is invalid.")
        self._api_key = api_key.strip()
        self._transport = transport
        self._base_url = NVIDIA_NIM_API_BASE
        self._budget = budget
        self._monotonic = monotonic

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> NvidiaNimClient:
        source = os.environ if environment is None else environment
        try:
            budget = load_provider_budget(
                source,
                prefix="AI_VASTU_NVIDIA",
                default=DEFAULT_NVIDIA_NIM_BUDGET,
            )
        except ProviderBudgetConfigurationError as exc:
            raise NvidiaNimConfigurationError("NVIDIA NIM runtime budget is invalid.") from exc
        return cls(
            api_key=source.get("NVIDIA_API_KEY", ""),
            base_url=source.get(
                "AI_VASTU_NVIDIA_BASE_URL",
                NVIDIA_NIM_API_BASE,
            ),
            budget=budget,
            transport=transport,
        )

    def complete_validated_json(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        models: Sequence[str],
        validator: Callable[[dict[str, Any], str], T],
        temperature: float,
        max_tokens: int | None = None,
        response_format: Mapping[str, Any] | None = None,
        disable_thinking: bool = False,
    ) -> T:
        chain = _approved_chain(models)
        json_response_format = _validated_response_format(response_format)
        if not isinstance(disable_thinking, bool):
            raise NvidiaNimConfigurationError(
                "NVIDIA NIM disable_thinking must be a boolean."
            )
        if disable_thinking and chain != (VISION_MODEL,):
            raise NvidiaNimConfigurationError(
                "NVIDIA NIM thinking control is restricted to the pinned vision model."
            )
        if max_tokens is not None and (
            isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0
        ):
            raise NvidiaNimConfigurationError("NVIDIA NIM max_tokens must be a positive integer.")

        deadline = self._monotonic() + self._budget.total_timeout_seconds
        model = chain[0]
        with httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept-Encoding": "identity",
            },
            timeout=self._budget.attempt_timeout_seconds,
            transport=self._transport,
        ) as client:
            for attempt_index in range(2):
                attempts = attempt_index + 1
                remaining = deadline - self._monotonic()
                if remaining <= 0:
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.TIMEOUT,
                        model_id=model,
                        attempts=max(1, attempt_index),
                    )

                body: dict[str, Any] = {
                    "model": model,
                    "messages": list(messages),
                    "temperature": temperature,
                }
                if max_tokens is not None:
                    body["max_tokens"] = max_tokens
                if disable_thinking:
                    body["chat_template_kwargs"] = {"enable_thinking": False}
                if (
                    json_response_format is not None
                    and model == INACTIVE_UNQUALIFIED_TEXT_MODEL
                ):
                    body["response_format"] = json_response_format

                try:
                    with client.stream(
                        "POST",
                        "/chat/completions",
                        json=body,
                        timeout=min(
                            self._budget.attempt_timeout_seconds,
                            remaining,
                        ),
                    ) as response:
                        if self._monotonic() >= deadline:
                            raise NvidiaNimRequestError(
                                ProviderFailureCategory.TIMEOUT,
                                model_id=model,
                                attempts=attempts,
                            )
                        if not response.is_success:
                            category = _status_category(response.status_code)
                            if attempt_index == 0 and category in {
                                ProviderFailureCategory.UNAVAILABLE,
                                ProviderFailureCategory.TIMEOUT,
                            }:
                                continue
                            raise NvidiaNimRequestError(
                                category,
                                http_status=response.status_code,
                                model_id=model,
                                attempts=attempts,
                            )

                        response_bytes = read_limited_provider_response(
                            response,
                            provider=NVIDIA_NIM_PROVIDER,
                            deadline=deadline,
                            monotonic=self._monotonic,
                        )
                except ProviderRuntimeError as exc:
                    if isinstance(exc, NvidiaNimRequestError):
                        raise
                    if (
                        attempt_index == 0
                        and exc.category is ProviderFailureCategory.TIMEOUT
                    ):
                        continue
                    raise NvidiaNimRequestError(
                        exc.category,
                        model_id=model,
                        attempts=attempts,
                    ) from None
                except httpx.TransportError as exc:
                    category = _transport_category(exc)
                    if attempt_index == 0 and _eligible_transport_failure(exc):
                        continue
                    raise NvidiaNimRequestError(
                        category,
                        model_id=model,
                        attempts=attempts,
                    ) from None

                if self._monotonic() >= deadline:
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.TIMEOUT,
                        model_id=model,
                        attempts=attempts,
                    )
                try:
                    raw_payload = json.loads(response_bytes)
                    if not isinstance(raw_payload, dict):
                        raise ValueError
                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    TypeError,
                    ValueError,
                    KeyError,
                ):
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.INVALID_RESPONSE,
                        stage=NvidiaNimFailureStage.STRICT_JSON,
                        model_id=model,
                        attempts=attempts,
                    ) from None
                if raw_payload.get("model") != model:
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.INVALID_RESPONSE,
                        stage=NvidiaNimFailureStage.PROVENANCE,
                        model_id=model,
                        attempts=attempts,
                    )
                try:
                    parsed = _strict_json_object(_message_text(raw_payload))
                except (TypeError, ValueError, KeyError):
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.INVALID_RESPONSE,
                        stage=NvidiaNimFailureStage.STRICT_JSON,
                        model_id=model,
                        attempts=attempts,
                    ) from None
                try:
                    validated = validator(parsed, model)
                except Exception:
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.INVALID_RESPONSE,
                        stage=NvidiaNimFailureStage.APPLICATION_VALIDATION,
                        model_id=model,
                        attempts=attempts,
                    ) from None
                if self._monotonic() >= deadline:
                    raise NvidiaNimRequestError(
                        ProviderFailureCategory.TIMEOUT,
                        model_id=model,
                        attempts=attempts,
                    )
                return validated

        raise NvidiaNimRequestError(ProviderFailureCategory.UNAVAILABLE)

    def verify_pinned_models_available(self) -> tuple[str, str]:
        """Verify the exact Vastudraw pins before any completion probe."""

        deadline = self._monotonic() + self._budget.total_timeout_seconds
        try:
            with httpx.Client(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept-Encoding": "identity",
                },
                timeout=self._budget.attempt_timeout_seconds,
                transport=self._transport,
            ) as client, client.stream(
                "GET",
                "/models",
                timeout=min(
                    self._budget.attempt_timeout_seconds,
                    self._budget.total_timeout_seconds,
                ),
            ) as response:
                if self._monotonic() >= deadline:
                    raise NvidiaNimRequestError(ProviderFailureCategory.TIMEOUT)
                if not response.is_success:
                    raise NvidiaNimRequestError(
                        _status_category(response.status_code),
                        http_status=response.status_code,
                    )
                response_bytes = read_limited_provider_response(
                    response,
                    provider=NVIDIA_NIM_PROVIDER,
                    deadline=deadline,
                    monotonic=self._monotonic,
                )
        except ProviderRuntimeError as exc:
            if isinstance(exc, NvidiaNimRequestError):
                raise
            raise NvidiaNimRequestError(exc.category) from None
        except httpx.TransportError as exc:
            raise NvidiaNimRequestError(_transport_category(exc)) from None

        try:
            payload = json.loads(response_bytes)
            if not isinstance(payload, dict):
                raise ValueError
            data = payload.get("data")
            if not isinstance(data, list):
                raise ValueError
            if any(
                not isinstance(item, dict) or not isinstance(item.get("id"), str)
                for item in data
            ):
                raise ValueError
            available = {item["id"] for item in data}
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError, KeyError):
            raise NvidiaNimRequestError(ProviderFailureCategory.INVALID_RESPONSE) from None

        pinned = (PRIMARY_TEXT_MODEL, VISION_MODEL)
        if any(model not in available for model in pinned):
            raise NvidiaNimRequestError(ProviderFailureCategory.INVALID_RESPONSE)
        return pinned


def schema_instruction(schema: dict[str, Any]) -> str:
    return (
        "Return one JSON object only. It must validate against this application "
        "schema. Do not wrap it in markdown or add prose.\nSCHEMA:\n"
        + json.dumps(
            schema,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )
