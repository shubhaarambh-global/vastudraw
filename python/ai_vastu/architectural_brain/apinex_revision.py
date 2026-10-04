from __future__ import annotations

import json
from uuid import UUID

from ai_vastu.apinex_http import ApinexClient
from ai_vastu.provider_runtime import ProviderRuntimeError

from .models import RevisionOperation, StructuredRevisionIntent


def interpret_revision_with_apinex(
    *, project_id: UUID, base_revision_id: UUID, request: str
) -> StructuredRevisionIntent:
    client = ApinexClient.from_environment()
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

    def validate(parsed: dict[str, object], _model: str) -> StructuredRevisionIntent:
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
                        "Do not emit geometry or coordinates."
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
            schema=StructuredRevisionIntent.model_json_schema(),
            validator=validate,
        )
    except ProviderRuntimeError as exc:
        raise RuntimeError("APINEX revision interpretation failed.") from exc
