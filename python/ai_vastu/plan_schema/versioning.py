from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .models import PLAN_SCHEMA_VERSION, PlanDocument


class UnsupportedSchemaVersion(ValueError):
    pass


def migrate_plan_document_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Migrate supported historical PlanDocument payloads to current schema."""

    version = payload.get("schema_version")

    if version == PLAN_SCHEMA_VERSION:
        return deepcopy(payload)

    if version == "1.0.0":
        migrated = deepcopy(payload)

        floors = migrated.get("floors")
        if not isinstance(floors, list):
            raise ValueError("PlanDocument 1.0.0 migration requires floors to be an array.")

        for floor in floors:
            if not isinstance(floor, dict):
                raise ValueError("PlanDocument 1.0.0 migration requires floor objects.")
            floor.setdefault("site_spaces", [])

        migrated["schema_version"] = PLAN_SCHEMA_VERSION

        # A canonical hash from 1.0.0 cannot remain authoritative after the
        # schema and canonical payload change. The parser recomputes it.
        migrated["content_hash"] = None

        return migrated

    raise UnsupportedSchemaVersion(
        f"No migration path exists from schema_version {version!r} to {PLAN_SCHEMA_VERSION!r}."
    )


def parse_plan_document_json(
    payload: str | bytes,
) -> PlanDocument:
    """Parse current or explicitly migratable canonical PlanDocument JSON."""

    raw: Any = json.loads(payload)
    if not isinstance(raw, dict):
        raise ValueError("PlanDocument JSON root must be an object.")

    original_version = raw.get("schema_version")
    migrated = migrate_plan_document_payload(raw)

    # FrozenModel is intentionally strict in Python mode. A PlanDocument
    # arriving from JSON must therefore be validated in Pydantic's JSON mode,
    # where canonical JSON strings/arrays are decoded into UUIDs, enums and
    # tuples exactly as the original parser did.
    migrated_json = json.dumps(
        migrated,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    document = PlanDocument.model_validate_json(
        migrated_json
    )

    if original_version != PLAN_SCHEMA_VERSION:
        return document.with_content_hash()

    return document
