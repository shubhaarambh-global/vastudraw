from __future__ import annotations

import json
import os
from typing import Any

import httpx

from ..errors import VastuReasoningConfigurationError
from ..models import VastuReasoningProfile
from .base import VastuReasoningInput

_SYSTEM = """Reason only over the supplied source-backed Vastu rule catalog.
Never invent rules, sectors, or hard constraints.
Return exactly one reasoning entry for EVERY catalog rule, using NOT_APPLICABLE
where appropriate. Vastu remains a soft planning
influence and never overrides safety, law, geometry validity, circulation, usable
dimensions, structure, or explicit client must-haves. Preserve source disagreement.
Return only the supplied JSON schema."""


def _output_text(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    output = data.get("output")
    if isinstance(output, list):
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
    raise RuntimeError("OpenAI Vastu response did not contain output_text.")


class OpenAIVastuReasoningProvider:
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise VastuReasoningConfigurationError(
                "OPENAI_API_KEY is required for Vastu reasoning."
            )
        if not model:
            raise VastuReasoningConfigurationError(
                "AI_VASTU_VASTU_MODEL is required; no model is guessed."
            )
        self._api_key = api_key
        self._model = model
        self._transport = transport

    @classmethod
    def from_environment(cls) -> OpenAIVastuReasoningProvider:
        model = os.getenv("AI_VASTU_VASTU_MODEL", "").strip()
        return cls(api_key=os.getenv("OPENAI_API_KEY", ""), model=model)

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile:
        payload = {
            "model": self._model,
            "store": False,
            "instructions": _SYSTEM,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                {
                                    "original_client_brief": request.original_prompt,
                                    "confirmed_requirements": request.confirmed.model_dump(
                                        mode="json"
                                    ),
                                    "soft_vastu_catalog": request.catalog.model_dump(mode="json"),
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        }
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "ai_vastu_reasoning_profile",
                    "strict": True,
                    "schema": VastuReasoningProfile.model_json_schema(),
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
                data = response.json()
            parsed = json.loads(_output_text(data))
            parsed.update(
                {
                    "schema_version": "26B.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": self._model,
                    "influence_mode": "balanced",
                    "architecture_weight_basis_points": 5000,
                    "vastu_weight_basis_points": 5000,
                    "content_hash": None,
                }
            )
            return VastuReasoningProfile.model_validate(parsed).with_content_hash()
        except Exception as exc:
            raise RuntimeError(f"OpenAI Vastu reasoning failed: {exc}") from exc
