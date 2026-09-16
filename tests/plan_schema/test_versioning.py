import json

import pytest

from ai_vastu.plan_schema import UnsupportedSchemaVersion, parse_plan_document_json

from .sample import sample_plan


def test_current_schema_parses() -> None:
    parsed = parse_plan_document_json(sample_plan().to_canonical_json())
    assert parsed.schema_version == "1.0.0"


def test_unknown_schema_version_fails_closed() -> None:
    payload = json.loads(sample_plan().to_canonical_json())
    payload["schema_version"] = "99.0.0"
    with pytest.raises(UnsupportedSchemaVersion):
        parse_plan_document_json(json.dumps(payload))
