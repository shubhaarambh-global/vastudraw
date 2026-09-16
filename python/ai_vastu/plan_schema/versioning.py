from __future__ import annotations

import json
from typing import Any

from .models import PLAN_SCHEMA_VERSION, PlanDocument


class UnsupportedSchemaVersion(ValueError):
    pass


def parse_plan_document_json(payload: str | bytes) -> PlanDocument:
    """Parse a canonical PlanDocument and fail closed on unknown schema versions."""

    raw: Any = json.loads(payload)
    if not isinstance(raw, dict):
        raise ValueError("PlanDocument JSON root must be an object.")
    version = raw.get("schema_version")
    if version != PLAN_SCHEMA_VERSION:
        raise UnsupportedSchemaVersion(
            "Unsupported PlanDocument schema_version "
            f"{version!r}; expected {PLAN_SCHEMA_VERSION!r}."
        )
    return PlanDocument.model_validate_json(payload)


def migrate_plan_document_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Migration entry point; Phase 1 has no older production schema to migrate."""

    version = payload.get("schema_version")
    if version == PLAN_SCHEMA_VERSION:
        return payload.copy()
    raise UnsupportedSchemaVersion(
        f"No migration path exists from schema_version {version!r} to {PLAN_SCHEMA_VERSION!r}."
    )
