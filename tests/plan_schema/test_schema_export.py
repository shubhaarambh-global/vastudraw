import json
from pathlib import Path

from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION, plan_document_json_schema

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "packages/contracts/schema/plan-document.schema.json"


def test_committed_schema_matches_authoritative_pydantic_model() -> None:
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == plan_document_json_schema()


def test_schema_has_fixed_version_and_no_root_geometry_duplication() -> None:
    schema = plan_document_json_schema()
    properties = schema["properties"]
    assert properties["schema_version"]["const"] == PLAN_SCHEMA_VERSION
    assert "rooms" not in properties
    assert "walls" not in properties
