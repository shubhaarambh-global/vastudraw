from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ai_vastu.ollama_local_http import (
    OllamaLocalClient,
    OllamaLocalConfigurationError,
)
from ai_vastu.provider_runtime import ProviderRuntimeError

from ..errors import VastuReasoningConfigurationError, VastuReasoningProviderError
from ..models import SoftVastuCatalog, VastuReasoningProfile, VastuRuleReasoning
from .base import VastuReasoningInput

# Bound the private wire output to fit the shared context. Public rationale limit
# remains 1000; these stricter decoding limits never truncate generated text.
_WIRE_RATIONALE_MAX_LENGTH = 256
_WIRE_NOTE_MAX_LENGTH = 160
_WIRE_MAX_NOTES = 3

_SYSTEM = """You are the Vastu reasoning layer for an Indian residential
planning system. Reason only over the application-supplied source-backed catalog.

CRITICAL POLICY:
- Vastu remains a SOFT design influence only.
- Never invent rules or turn a principle into a hard geometry constraint.
- Never override safety, statutory requirements, confirmed must-haves, usable
  dimensions, circulation, accessibility, structure, or deterministic geometry.
- Do not change catalog sectors or invent rule IDs.
- Return one entry for every catalog rule.
- Return rules as an object keyed by catalog rule ID, not an array.
- Return only rules and notes; application metadata is supplied by the application.
- Keep each rationale to one concise sentence, at most 256 characters.
- Return at most three notes, each at most 160 characters.
- Preserve non-adjustable defaults and source disagreement.
- For every catalog rule, importance MUST be one of that rule's allowed_importance values.
- For every catalog rule, flexibility MUST be one of that rule's allowed_flexibility values.
- If uncertain, use that rule's default_importance and default_flexibility.
- Return one strict JSON object only.
"""


def _catalog_output_schema(catalog: SoftVastuCatalog) -> dict[str, Any]:
    """Private wire contract: ordinary object properties avoid tuple grammar support."""
    rule_schema = VastuRuleReasoning.model_json_schema()
    properties: dict[str, Any] = {}
    for rule in catalog.rules:
        entry = deepcopy(rule_schema)
        entry.pop("$defs", None)
        fields = entry["properties"]
        fields["rule_id"] = {"type": "string", "enum": [rule.rule_id]}
        fields["importance"] = {
            "type": "string",
            "enum": [value.value for value in rule.allowed_importance],
        }
        fields["flexibility"] = {
            "type": "string",
            "enum": [value.value for value in rule.allowed_flexibility],
        }
        fields["rationale"]["maxLength"] = _WIRE_RATIONALE_MAX_LENGTH
        if not rule.reasoning_adjustable:
            fields["weight_multiplier_basis_points"]["enum"] = [10_000]
        entry["required"] = list(fields)
        properties[rule.rule_id] = entry
    return {
        "type": "object",
        "additionalProperties": False,
        "$defs": rule_schema["$defs"],
        "properties": {
            "rules": {
                "type": "object",
                "additionalProperties": False,
                "properties": properties,
                "required": list(properties),
            },
            "notes": {
                "type": "array",
                "maxItems": _WIRE_MAX_NOTES,
                "items": {"type": "string", "minLength": 1, "maxLength": _WIRE_NOTE_MAX_LENGTH},
            },
        },
        "required": ["rules", "notes"],
    }


def _validate_catalog_output(
    parsed: dict[str, Any], catalog: SoftVastuCatalog
) -> tuple[VastuRuleReasoning, ...]:
    # Validate even if a provider ignores the decoding schema. No repair or clamping.
    if set(parsed) != {"rules", "notes"}:
        raise ValueError("Invalid Vastu wire fields.")
    if (
        not isinstance(parsed["notes"], list)
        or len(parsed["notes"]) > _WIRE_MAX_NOTES
        or not all(
            isinstance(note, str) and 1 <= len(note) <= _WIRE_NOTE_MAX_LENGTH
            for note in parsed["notes"]
        )
    ):
        raise ValueError("Invalid Vastu wire notes.")
    entries = parsed["rules"]
    if not isinstance(entries, dict) or set(entries) != {rule.rule_id for rule in catalog.rules}:
        raise ValueError("Invalid Vastu wire rule set.")
    result: list[VastuRuleReasoning] = []
    for rule in catalog.rules:
        entry = entries[rule.rule_id]
        if (
            not isinstance(entry, dict)
            or set(entry) != set(VastuRuleReasoning.model_fields)
            or type(entry["weight_multiplier_basis_points"]) is not int
        ):
            raise ValueError("Invalid Vastu wire rule fields.")
        item = VastuRuleReasoning.model_validate(entry)
        if (
            item.rule_id != rule.rule_id
            or item.importance not in rule.allowed_importance
            or item.flexibility not in rule.allowed_flexibility
            or (not rule.reasoning_adjustable and item.weight_multiplier_basis_points != 10_000)
            or len(item.rationale) > _WIRE_RATIONALE_MAX_LENGTH
        ):
            raise ValueError("Invalid Vastu wire catalog policy.")
        result.append(item)
    return tuple(result)


class OllamaLocalVastuReasoningProvider:
    name = "ollama_local"

    def __init__(self, *, client: OllamaLocalClient) -> None:
        self._client = client

    @classmethod
    def from_environment(cls) -> OllamaLocalVastuReasoningProvider:
        try:
            return cls(client=OllamaLocalClient.from_environment())
        except OllamaLocalConfigurationError as exc:
            raise VastuReasoningConfigurationError(
                "Local Ollama Vastu reasoning provider is not configured."
            ) from exc

    def reason(self, request: VastuReasoningInput) -> VastuReasoningProfile:
        user_text = json.dumps(
            {
                "original_client_brief": request.original_prompt,
                "confirmed_requirements": request.confirmed.model_dump(mode="json"),
                "soft_vastu_catalog": request.catalog.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        def validate(parsed: dict[str, Any], model: str) -> VastuReasoningProfile:
            rules = _validate_catalog_output(parsed, request.catalog)
            payload = {
                "rules": [rule.model_dump(mode="json") for rule in rules],
                "notes": parsed["notes"],
            }
            payload.update(
                {
                    "schema_version": "26B.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": model,
                    "influence_mode": "balanced",
                    "architecture_weight_basis_points": 5000,
                    "vastu_weight_basis_points": 5000,
                    "content_hash": None,
                }
            )
            return VastuReasoningProfile.model_validate_json(
                json.dumps(payload)
            ).with_content_hash()

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_text},
                ),
                schema=_catalog_output_schema(request.catalog),
                validator=validate,
            )
        except ProviderRuntimeError as exc:
            raise VastuReasoningProviderError(exc.category) from exc
