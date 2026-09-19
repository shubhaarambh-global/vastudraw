import json

import pytest

from ai_vastu.plan_schema import (
    PLAN_SCHEMA_VERSION,
    UnsupportedSchemaVersion,
    migrate_plan_document_payload,
    parse_plan_document_json,
)

from .sample import sample_plan


def test_current_schema_parses() -> None:
    parsed = parse_plan_document_json(sample_plan().to_canonical_json())

    assert parsed.schema_version == PLAN_SCHEMA_VERSION
    assert parsed.schema_version == "1.1.0"


def test_legacy_1_0_0_migrates_with_empty_site_spaces() -> None:
    payload = json.loads(sample_plan().to_canonical_json())

    payload["schema_version"] = "1.0.0"
    payload["content_hash"] = None

    for floor in payload["floors"]:
        floor.pop("site_spaces", None)

    migrated = migrate_plan_document_payload(payload)

    assert migrated["schema_version"] == "1.1.0"
    assert all(floor["site_spaces"] == [] for floor in migrated["floors"])

    parsed = parse_plan_document_json(json.dumps(payload))

    assert parsed.schema_version == "1.1.0"
    assert all(floor.site_spaces == () for floor in parsed.floors)
    assert parsed.content_hash is not None


def test_unknown_schema_version_fails_closed() -> None:
    payload = json.loads(sample_plan().to_canonical_json())
    payload["schema_version"] = "99.0.0"

    with pytest.raises(UnsupportedSchemaVersion):
        parse_plan_document_json(json.dumps(payload))
