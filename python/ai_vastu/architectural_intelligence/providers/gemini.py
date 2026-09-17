from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import ValidationError

from ai_vastu.gemini_http import post_json_with_retry

from ..errors import (
    ArchitecturalIntelligenceConfigurationError,
    ArchitecturalIntelligenceProviderError,
)
from ..models import ArchitecturalDesignIntent
from .base import ArchitecturalReasoningInput
from .schema_utils import sanitize_gemini_schema

_SYSTEM = """You are the architectural reasoning layer for an Indian residential
planning system.

Act as a senior residential architect converting a confirmed client program into
STRUCTURED SOFT DESIGN INTENT for a deterministic solver.

Focus on functional zoning, entrance sequence, living-dining-kitchen
relationships, bedroom privacy, practical toilet access and visual privacy,
wardrobe/furniture needs stated by the client, daylight, ventilation,
service/plumbing clustering, short legible circulation, parking access, and
avoiding unusable leftover spaces.

CRITICAL AUTHORITY BOUNDARY:
- Do NOT draw authoritative geometry.
- Do NOT output coordinates, walls, doors, polygons, or a finished floor plan.
- Do NOT invent exact room dimensions. preferred_* dimensions may be populated
  only when the client explicitly stated that dimension in the supplied brief
  or confirmed room notes.
- Do NOT create hard architectural constraints from your own judgement.
- Do NOT apply Vastu placement rules in Phase 26A. Vastu weighting is a separate
  Phase 26B scoring layer.
- Safety, geometry validity, client-confirmed requirements and future statutory
  constraints outrank your suggestions.
- Preserve ambiguity in warnings/planning_notes.
- Return only the supplied JSON schema.
"""


def _extract_text(result: dict[str, Any]) -> str:
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ArchitecturalIntelligenceProviderError("Gemini response did not contain candidates.")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise ArchitecturalIntelligenceProviderError("Unexpected Gemini candidate.")
    content = candidate.get("content")
    if not isinstance(content, dict):
        raise ArchitecturalIntelligenceProviderError("Gemini response did not contain content.")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ArchitecturalIntelligenceProviderError("Gemini response did not contain parts.")
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    raise ArchitecturalIntelligenceProviderError("Gemini response did not contain text output.")


class GeminiArchitecturalIntelligenceProvider:
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
            raise ArchitecturalIntelligenceConfigurationError(
                "GEMINI_API_KEY is required for architectural reasoning."
            )
        if not model:
            raise ArchitecturalIntelligenceConfigurationError(
                "AI_VASTU_ARCHITECT_MODEL is required; no live model is guessed."
            )
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(cls) -> GeminiArchitecturalIntelligenceProvider:
        model = os.getenv("AI_VASTU_ARCHITECT_MODEL", "").strip()
        if not model:
            model = os.getenv("AI_VASTU_GEMINI_MODEL", "").strip()
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=model,
        )

    def reason(
        self,
        request: ArchitecturalReasoningInput,
    ) -> ArchitecturalDesignIntent:
        confirmed_json = json.dumps(
            request.confirmed.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        user_text = (
            "Original client brief:\n"
            + request.original_prompt
            + "\n\nHuman-confirmed planning requirements:\n"
            + confirmed_json
        )

        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseJsonSchema": sanitize_gemini_schema(
                    ArchitecturalDesignIntent.model_json_schema()
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
                result = response.json()

            if not isinstance(result, dict):
                raise ArchitecturalIntelligenceProviderError("Unexpected Gemini response.")
            parsed = json.loads(_extract_text(result))
            if not isinstance(parsed, dict):
                raise ArchitecturalIntelligenceProviderError(
                    "Gemini structured output was not an object."
                )

            parsed.update(
                {
                    "schema_version": "26A.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": self._model,
                    "content_hash": None,
                }
            )
            return ArchitecturalDesignIntent.model_validate(parsed).with_content_hash()
        except ArchitecturalIntelligenceProviderError:
            raise
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as exc:
            raise ArchitecturalIntelligenceProviderError(
                f"Gemini architectural reasoning failed: {exc}"
            ) from exc
