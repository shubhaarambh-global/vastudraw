from __future__ import annotations

import base64
import json
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx

PRIMARY_ARCHITECTURAL_MODEL = "deepseek/deepseek-v4-flash-0731:free"
VISION_PLAN_MODEL = "inclusionai/ling-3.0-flash-vl:free"
FALLBACK_REASONING_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

APPROVED_FREE_MODELS = frozenset(
    {
        PRIMARY_ARCHITECTURAL_MODEL,
        VISION_PLAN_MODEL,
        FALLBACK_REASONING_MODEL,
    }
)
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

FREE_PDF_PLUGIN: tuple[dict[str, Any], ...] = (
    {
        "id": "file-parser",
        "pdf": {"engine": "cloudflare-ai"},
    },
)

T = TypeVar("T")


class OpenRouterConfigurationError(RuntimeError):
    pass


class OpenRouterRequestError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class OpenRouterModelPolicy:
    primary: str = PRIMARY_ARCHITECTURAL_MODEL
    vision: str = VISION_PLAN_MODEL
    fallback: str = FALLBACK_REASONING_MODEL

    @classmethod
    def from_environment(cls) -> OpenRouterModelPolicy:
        policy = cls(
            primary=os.getenv(
                "AI_VASTU_OPENROUTER_PRIMARY_MODEL",
                PRIMARY_ARCHITECTURAL_MODEL,
            ).strip(),
            vision=os.getenv(
                "AI_VASTU_OPENROUTER_VISION_MODEL",
                VISION_PLAN_MODEL,
            ).strip(),
            fallback=os.getenv(
                "AI_VASTU_OPENROUTER_FALLBACK_MODEL",
                FALLBACK_REASONING_MODEL,
            ).strip(),
        )
        policy.validate()
        return policy

    def validate(self) -> None:
        expected = {
            "primary": PRIMARY_ARCHITECTURAL_MODEL,
            "vision": VISION_PLAN_MODEL,
            "fallback": FALLBACK_REASONING_MODEL,
        }
        actual = {
            "primary": self.primary,
            "vision": self.vision,
            "fallback": self.fallback,
        }
        for role, model in actual.items():
            if model not in APPROVED_FREE_MODELS:
                raise OpenRouterConfigurationError(
                    f"{role} OpenRouter model is not in the approved free-only set: {model!r}."
                )
            if not model.endswith(":free"):
                raise OpenRouterConfigurationError(
                    f"{role} OpenRouter model must use an explicit :free route."
                )
            if model != expected[role]:
                raise OpenRouterConfigurationError(
                    f"{role} OpenRouter model must remain pinned to {expected[role]!r}."
                )

    @property
    def reasoning_chain(self) -> tuple[str, ...]:
        if self.primary == self.fallback:
            return (self.primary,)
        return (self.primary, self.fallback)

    @property
    def vision_chain(self) -> tuple[str, ...]:
        return (self.vision,)


def _approved(model: str) -> str:
    if model not in APPROVED_FREE_MODELS or not model.endswith(":free"):
        raise OpenRouterConfigurationError(
            f"Refusing non-approved or non-free OpenRouter model: {model!r}."
        )
    return model


def image_url_part(content_type: str, data: bytes) -> dict[str, Any]:
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError(f"Unsupported OpenRouter image media type: {content_type}.")
    encoded = base64.b64encode(data).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:{content_type};base64,{encoded}",
        },
    }


def pdf_file_part(filename: str, data: bytes) -> dict[str, Any]:
    encoded = base64.b64encode(data).decode("ascii")
    return {
        "type": "file",
        "file": {
            "filename": filename,
            "file_data": f"data:application/pdf;base64,{encoded}",
        },
    }


def extract_json_object(text: str) -> dict[str, Any]:
    normalized = text.strip()
    if normalized.startswith("```"):
        normalized = re_strip_code_fence(normalized)
    start = normalized.find("{")
    end = normalized.rfind("}")
    if start < 0 or end < start:
        raise ValueError("OpenRouter response did not contain a JSON object.")
    parsed = json.loads(normalized[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("OpenRouter structured output was not a JSON object.")
    return parsed


def re_strip_code_fence(value: str) -> str:
    lines = value.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _message_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("OpenRouter response did not contain choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("OpenRouter response choice was malformed.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("OpenRouter response did not contain a message.")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(str(part["text"]))
        if texts:
            return "\n".join(texts)
    raise ValueError("OpenRouter response did not contain text content.")


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        base_url: str = OPENROUTER_API_BASE,
        timeout_seconds: float = 120.0,
    ) -> None:
        if not api_key.strip():
            raise OpenRouterConfigurationError("OPENROUTER_API_KEY is required.")
        if base_url.rstrip("/") != OPENROUTER_API_BASE:
            raise OpenRouterConfigurationError(
                "OpenRouter runtime base URL is pinned to https://openrouter.ai/api/v1."
            )
        self._api_key = api_key.strip()
        self._transport = transport
        self._base_url = OPENROUTER_API_BASE
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> OpenRouterClient:
        return cls(api_key=os.getenv("OPENROUTER_API_KEY", ""))

    def complete_validated_json(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        models: Sequence[str],
        validator: Callable[[dict[str, Any], str], T],
        temperature: float,
        plugins: Sequence[dict[str, Any]] = (),
    ) -> T:
        if not models:
            raise OpenRouterConfigurationError(
                "At least one approved OpenRouter model is required."
            )

        failures: list[str] = []
        for requested_model in models:
            model = _approved(requested_model)
            body: dict[str, Any] = {
                "model": model,
                "messages": list(messages),
                "temperature": temperature,
            }
            if plugins:
                body["plugins"] = list(plugins)

            try:
                with httpx.Client(
                    base_url=self._base_url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = client.post("/chat/completions", json=body)
                    response.raise_for_status()
                    raw_payload = response.json()

                if not isinstance(raw_payload, dict):
                    raise ValueError("OpenRouter returned a non-object response.")
                parsed = extract_json_object(_message_text(raw_payload))
                return validator(parsed, model)
            except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                failures.append(f"{model}: {type(exc).__name__}: {exc}")

        detail = " | ".join(failures)
        raise OpenRouterRequestError(
            "All explicitly approved free OpenRouter models failed. " + detail
        )


def schema_instruction(schema: dict[str, Any]) -> str:
    return (
        "Return one JSON object only. It must validate against this application schema. "
        "Do not wrap it in markdown.\nSCHEMA:\n"
        + json.dumps(schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
