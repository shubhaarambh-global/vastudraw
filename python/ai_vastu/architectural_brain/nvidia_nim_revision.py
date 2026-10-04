from __future__ import annotations

import json
from uuid import UUID

from ai_vastu.nvidia_nim_http import (
    NvidiaNimClient,
    NvidiaNimModelPolicy,
    NvidiaNimRequestError,
    schema_instruction,
)

from .models import RevisionOperation, StructuredRevisionIntent


def interpret_revision_with_nvidia_nim(
    *,
    project_id: UUID,
    base_revision_id: UUID,
    request: str,
) -> StructuredRevisionIntent:
    client = NvidiaNimClient.from_environment()
    policy = NvidiaNimModelPolicy.from_environment()
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
    user_text = json.dumps(
        prompt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    user_text += "\n\n" + schema_instruction(StructuredRevisionIntent.model_json_schema())

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
                        "Do not emit geometry or coordinates. Return JSON only."
                    ),
                },
                {"role": "user", "content": user_text},
            ),
            models=policy.text_chain,
            validator=validate,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    except NvidiaNimRequestError as exc:
        raise RuntimeError("NVIDIA NIM revision interpretation failed.") from exc
