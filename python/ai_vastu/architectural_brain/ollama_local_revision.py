from __future__ import annotations

import json
from uuid import UUID

from ai_vastu.ollama_local_http import OllamaLocalClient
from ai_vastu.provider_runtime import ProviderRuntimeError

from .models import RevisionOperation, StructuredRevisionIntent


def interpret_revision_with_ollama_local(
    *,
    project_id: UUID,
    base_revision_id: UUID,
    request: str,
    supported_room_types: tuple[str, ...] | None = None,
) -> StructuredRevisionIntent:
    client = OllamaLocalClient.from_environment()
    schema = StructuredRevisionIntent.model_json_schema()
    prompt = {
        "task": (
            "Convert a residential-plan revision request to advisory structured "
            "intent only. Never output CAD coordinates. Preserve every unmentioned "
            "requirement."
        ),
        "project_id": str(project_id),
        "base_revision_id": str(base_revision_id),
        "request": request,
        "operations": [item.value for item in RevisionOperation],
        "units": "millimetres",
    }
    if supported_room_types is not None:
        prompt["task"] = (
            "Interpret exactly one room WIDTH or DEPTH increase. Use INCREASE_DIMENSION "
            "and a positive delta_mm in millimetres (1 foot = 304.8 mm). "
            "Set target_mm, target_side, related_room_type and quantity to null; "
            "they do not apply to a dimension increase. Use an exact supported room_type. "
            "For unsupported or ambiguous requests return an empty directives list. "
            "Never output coordinates or alter other requirements."
        )
        prompt["operations"] = [RevisionOperation.INCREASE_DIMENSION.value]
        prompt["supported_room_types"] = list(supported_room_types)
        properties = schema["$defs"]["RevisionDirective"]["properties"]
        properties["operation"] = {"const": RevisionOperation.INCREASE_DIMENSION.value}
        properties["room_type"] = {"type": "string", "enum": list(supported_room_types)}
        properties["axis"] = {"type": "string", "enum": ["WIDTH", "DEPTH"]}
        properties["delta_mm"] = {"type": "integer", "minimum": 1, "maximum": 3000}
        schema["$defs"]["RevisionDirective"]["required"] = [
            "operation",
            "room_type",
            "axis",
            "delta_mm",
        ]
        for field in ("target_mm", "target_side", "related_room_type", "quantity"):
            properties[field] = {"type": "null"}
        schema["properties"]["directives"]["maxItems"] = 1

    def validate(
        parsed: dict[str, object],
        _model: str,
    ) -> StructuredRevisionIntent:
        payload = dict(parsed)
        payload.update(
            {
                "schema_version": "26D.1",
                "project_id": str(project_id),
                "base_revision_id": str(base_revision_id),
                "original_request": request,
                "preserve_unmentioned_requirements": True,
                "authoritative_geometry": False,
            }
        )
        return StructuredRevisionIntent.model_validate_json(json.dumps(payload))

    try:
        return client.complete_validated_json(
            messages=(
                {
                    "role": "system",
                    "content": (
                        "Interpret residential revisions into advisory structured intent. "
                        "Do not emit geometry or coordinates. Return strict JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        prompt,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ),
                },
            ),
            schema=schema,
            validator=validate,
        )
    except ProviderRuntimeError as exc:
        raise RuntimeError("Local Ollama revision interpretation failed.") from exc
