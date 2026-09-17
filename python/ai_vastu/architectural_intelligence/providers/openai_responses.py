from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import ValidationError

from ..errors import (
    ArchitecturalIntelligenceConfigurationError,
    ArchitecturalIntelligenceProviderError,
)
from ..models import ArchitecturalDesignIntent
from .base import ArchitecturalReasoningInput

_SYSTEM = """You are the architectural reasoning layer for an Indian residential
planning system.

Convert the original client brief plus human-confirmed requirements into
STRUCTURED SOFT DESIGN INTENT.

Reason about functional zoning, entrance/privacy sequence, living-dining-kitchen
relationships, bedroom privacy, toilets, wardrobe/furniture needs explicitly
requested by the client, daylight, ventilation, plumbing/service clustering,
parking access and short legible circulation.

AUTHORITY BOUNDARY:
- Never draw authoritative geometry or output coordinates/walls/polygons.
- Never invent exact dimensions. preferred_* dimensions are allowed only if the
  supplied client brief or confirmed notes explicitly state them.
- Never create hard constraints from your own judgement.
- Do not apply Vastu placement rules in Phase 26A; Vastu is a separate weighted
  Phase 26B layer.
- Preserve ambiguity as notes/warnings.
- Return only the supplied JSON schema.
"""


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    output = response.get("output")
    if not isinstance(output, list):
        raise ArchitecturalIntelligenceProviderError("OpenAI response did not contain output.")
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                return str(part["text"])
    raise ArchitecturalIntelligenceProviderError("OpenAI response did not contain output_text.")


class OpenAIResponsesArchitecturalIntelligenceProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ArchitecturalIntelligenceConfigurationError(
                "OPENAI_API_KEY is required for architectural reasoning."
            )
        if not model:
            raise ArchitecturalIntelligenceConfigurationError(
                "AI_VASTU_ARCHITECT_MODEL is required; no live model is guessed."
            )
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(
        cls,
    ) -> OpenAIResponsesArchitecturalIntelligenceProvider:
        model = os.getenv("AI_VASTU_ARCHITECT_MODEL", "").strip()
        if not model:
            model = os.getenv("AI_VASTU_OPENAI_MODEL", "").strip()
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
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
        schema = ArchitecturalDesignIntent.model_json_schema()
        payload: dict[str, Any] = {
            "model": self._model,
            "store": False,
            "instructions": _SYSTEM,
            "input": [
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ai_vastu_architectural_design_intent",
                    "strict": True,
                    "schema": schema,
                }
            },
        }

        try:
            with httpx.Client(
                base_url="https://api.openai.com/v1",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=90.0,
                transport=self._transport,
            ) as client:
                response = client.post("/responses", json=payload)
                response.raise_for_status()
                result = response.json()

            if not isinstance(result, dict):
                raise ArchitecturalIntelligenceProviderError("Unexpected OpenAI response.")
            parsed = json.loads(_extract_output_text(result))
            if not isinstance(parsed, dict):
                raise ArchitecturalIntelligenceProviderError(
                    "OpenAI structured output was not an object."
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
                f"OpenAI architectural reasoning failed: {exc}"
            ) from exc
