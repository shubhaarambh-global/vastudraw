from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import ValidationError

from ai_vastu.gemini_http import post_json_with_retry

from ..errors import VastuReasoningConfigurationError
from ..models import VastuReasoningProfile
from .base import VastuReasoningInput
from .schema_utils import sanitize_gemini_schema

_SYSTEM = """You are the Vastu reasoning layer for an Indian residential
planning system.

You are NOT allowed to invent new Vastu rules. You may reason only over the
source-backed rule catalog supplied by the application.

Your task is contextual interpretation:
- decide whether a catalog rule is applicable to the confirmed program,
- classify its practical importance,
- classify how flexible the rule should be in this project,
- optionally reduce or increase its soft weight within the catalog policy,
- explain conflicts or source disagreement.

CRITICAL POLICY:
- Vastu is a SOFT design influence only.
- Never turn a Vastu principle into a hard geometry constraint.
- Never override safety, statutory requirements, client must-haves, usable room
  dimensions, circulation, accessibility, structure, or deterministic geometry validation.
- Do not change preferred/secondary/avoid sectors from the catalog.
- Do not invent rule IDs.
- Return exactly one reasoning entry for EVERY catalog rule, even when
  the correct applicability is NOT_APPLICABLE.
- Some catalog rules are marked reasoning_adjustable=false. Return their catalog
  default importance/flexibility unchanged.
- Source disagreement must remain visible.
- A rule may be NEGLIGIBLE, LOW, MODERATE, HIGH, or CORE while still remaining soft.
- Return only the supplied JSON schema.
"""


def _text(result: dict[str, Any]) -> str:
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini Vastu response did not contain candidates.")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise RuntimeError("Gemini Vastu response did not contain content.")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise RuntimeError("Gemini Vastu response did not contain parts.")
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    raise RuntimeError("Gemini Vastu response did not contain text.")


class GeminiVastuReasoningProvider:
    name = "gemini"
    API_BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise VastuReasoningConfigurationError(
                "GEMINI_API_KEY is required for Vastu reasoning."
            )
        if not model:
            raise VastuReasoningConfigurationError(
                "AI_VASTU_VASTU_MODEL is required; no model is guessed."
            )
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(cls) -> GeminiVastuReasoningProvider:
        model = os.getenv("AI_VASTU_VASTU_MODEL", "").strip()
        if not model:
            model = os.getenv("AI_VASTU_ARCHITECT_MODEL", "").strip()
        if not model:
            model = os.getenv("AI_VASTU_GEMINI_MODEL", "").strip()
        return cls(api_key=os.getenv("GEMINI_API_KEY", ""), model=model)

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile:
        catalog_payload = request.catalog.model_dump(mode="json")
        confirmed_payload = request.confirmed.model_dump(mode="json")
        user_text = json.dumps(
            {
                "original_client_brief": request.original_prompt,
                "confirmed_requirements": confirmed_payload,
                "soft_vastu_catalog": catalog_payload,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": 0.15,
                "responseMimeType": "application/json",
                "responseJsonSchema": sanitize_gemini_schema(
                    VastuReasoningProfile.model_json_schema()
                ),
            },
        }

        try:
            with httpx.Client(
                base_url=self.API_BASE,
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                timeout=90.0,
                transport=self._transport,
            ) as client:
                response = post_json_with_retry(
                    client,
                    f"/models/{self._model}:generateContent",
                    json_payload=payload,
                )
                data = response.json()
            if not isinstance(data, dict):
                raise RuntimeError("Unexpected Gemini Vastu response.")
            parsed = json.loads(_text(data))
            if not isinstance(parsed, dict):
                raise RuntimeError("Gemini Vastu structured output was not an object.")

            parsed.update(
                {
                    "schema_version": "26B.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": self._model,
                    # Application-owned after provider validation.
                    "influence_mode": "balanced",
                    "architecture_weight_basis_points": 5000,
                    "vastu_weight_basis_points": 5000,
                    "content_hash": None,
                }
            )
            return VastuReasoningProfile.model_validate(parsed).with_content_hash()
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError, RuntimeError) as exc:
            raise RuntimeError(f"Gemini Vastu reasoning failed: {exc}") from exc
