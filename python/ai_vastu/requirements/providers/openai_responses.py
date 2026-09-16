from __future__ import annotations

import base64
import json
import os
from typing import Any

import httpx

from ai_vastu.requirements.models import RequirementDraft
from ai_vastu.requirements.providers.base import InterpretationInput


class OpenAIRequirementsConfigurationError(RuntimeError):
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


def _data_url(content_type: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct:
        return direct

    output = response.get("output")
    if not isinstance(output, list):
        raise RuntimeError("OpenAI response did not contain output.")

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
    raise RuntimeError("OpenAI response did not contain output_text.")


class OpenAIResponsesRequirementsProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise OpenAIRequirementsConfigurationError("OPENAI_API_KEY is required.")
        if not model:
            raise OpenAIRequirementsConfigurationError(
                "AI_VASTU_OPENAI_MODEL is required; no live model is guessed."
            )
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(cls) -> OpenAIResponsesRequirementsProvider:
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("AI_VASTU_OPENAI_MODEL", ""),
        )

    def interpret(self, request: InterpretationInput) -> RequirementDraft:
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    "Project ID: "
                    + str(request.project_id)
                    + "\n\nClient brief:\n"
                    + request.prompt
                ),
            }
        ]

        for asset in request.references:
            data_url = _data_url(asset.content_type, asset.data)
            if asset.content_type in {"image/jpeg", "image/png"}:
                content.append(
                    {
                        "type": "input_image",
                        "image_url": data_url,
                        "detail": "high",
                    }
                )
            elif asset.content_type == "application/pdf":
                content.append(
                    {
                        "type": "input_file",
                        "filename": asset.filename,
                        "file_data": data_url,
                    }
                )

        schema = RequirementDraft.model_json_schema()
        payload: dict[str, Any] = {
            "model": self._model,
            "store": False,
            "instructions": _SYSTEM,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ai_vastu_requirement_draft",
                    "strict": True,
                    "schema": schema,
                }
            },
        }

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
            raise RuntimeError("Unexpected OpenAI response.")

        parsed = json.loads(_extract_output_text(result))
        draft = RequirementDraft.model_validate(parsed)

        # Identity is application authority, never model authority.
        return draft.model_copy(
            update={
                "draft_id": request.draft_id,
                "user_id": request.user_id,
                "project_id": request.project_id,
                "prompt": request.prompt,
                "reference_names": [item.filename for item in request.references],
                "provider": self.name,
                "model": self._model,
            }
        )
