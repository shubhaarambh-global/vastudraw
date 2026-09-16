from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

from ai_vastu.requirements.models import RequirementDraft
from ai_vastu.requirements.providers.base import InterpretationInput


class GeminiRequirementsConfigurationError(RuntimeError):
    pass


_SYSTEM = """You are the requirements interpreter for an Indian residential
architectural planning system.

Extract planning requirements from the user's prompt and attached reference files.

CRITICAL BOUNDARY:
- You do not draw authoritative geometry.
- You do not invent missing exact dimensions.
- Values inferred visually from images/PDFs must use source=image/pdf or
  source=model_inference and require confirmation.
- Do not assume property-facing direction equals road side.
- Do not assume road side equals true North.
- Preserve ambiguity in questions/warnings.
- Return only the supplied JSON schema.
"""

# Gemini structured output supports a useful subset of JSON Schema. Pydantic emits
# a few keywords outside that subset (for example const/default/minLength). Remove
# only unsupported presentation/validation keywords; Pydantic remains the final
# application-side validator.
_ALLOWED_SCHEMA_KEYS = {
    "$id",
    "$defs",
    "$ref",
    "$anchor",
    "type",
    "format",
    "title",
    "description",
    "enum",
    "items",
    "prefixItems",
    "minItems",
    "maxItems",
    "minimum",
    "maximum",
    "anyOf",
    "oneOf",
    "properties",
    "additionalProperties",
    "required",
}


def _sanitize_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [_sanitize_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    result: dict[str, Any] = {}
    if "const" in value:
        result["enum"] = [value["const"]]

    for key, item in value.items():
        if key == "const" or key not in _ALLOWED_SCHEMA_KEYS:
            continue
        if (
            (key == "properties" and isinstance(item, dict))
            or (key == "$defs" and isinstance(item, dict))
        ):
            result[key] = {
                str(name): _sanitize_schema(schema)
                for name, schema in item.items()
            }
        else:
            result[key] = _sanitize_schema(item)
    return result


def _inline_part(content_type: str, data: bytes) -> dict[str, Any]:
    return {
        "inlineData": {
            "mimeType": content_type,
            "data": base64.b64encode(data).decode("ascii"),
        }
    }


def _extract_text(result: dict[str, Any]) -> str:
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError("Gemini response did not contain candidates.")
    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise RuntimeError("Unexpected Gemini candidate.")
    content = candidate.get("content")
    if not isinstance(content, dict):
        raise RuntimeError("Gemini response did not contain content.")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise RuntimeError("Gemini response did not contain parts.")
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    raise RuntimeError("Gemini response did not contain text output.")


class GeminiGenerateContentRequirementsProvider:
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
            raise GeminiRequirementsConfigurationError("GEMINI_API_KEY is required.")
        if not model:
            raise GeminiRequirementsConfigurationError(
                "AI_VASTU_GEMINI_MODEL is required; no live model is guessed."
            )
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(cls) -> GeminiGenerateContentRequirementsProvider:
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("AI_VASTU_GEMINI_MODEL", ""),
        )

    def interpret(self, request: InterpretationInput) -> RequirementDraft:
        parts: list[dict[str, Any]] = [
            {
                "text": (
                    "Project ID: "
                    + str(request.project_id)
                    + "\n\nClient brief:\n"
                    + request.prompt
                )
            }
        ]
        for asset in request.references:
            if asset.content_type in {
                "image/jpeg",
                "image/png",
                "application/pdf",
            }:
                parts.append(_inline_part(asset.content_type, asset.data))

        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": _SYSTEM}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseJsonSchema": _sanitize_schema(
                    RequirementDraft.model_json_schema()
                ),
            },
        }

        with httpx.Client(
            base_url=self.API_BASE,
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=90.0,
            transport=self._transport,
        ) as client:
            response = client.post(
                f"/models/{self._model}:generateContent",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

        if not isinstance(result, dict):
            raise RuntimeError("Unexpected Gemini response.")

        parsed = json.loads(_extract_text(result))
        if not isinstance(parsed, dict):
            raise RuntimeError("Gemini structured output was not an object.")

        # Application identity is authoritative, never model authority.
        parsed.update(
            {
                "draft_id": str(request.draft_id),
                "user_id": str(request.user_id),
                "project_id": str(request.project_id),
                "prompt": request.prompt,
                "reference_names": [item.filename for item in request.references],
                "provider": self.name,
                "model": self._model,
            }
        )
        return RequirementDraft.model_validate(parsed)
