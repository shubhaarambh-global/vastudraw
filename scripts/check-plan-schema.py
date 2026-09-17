import json
from pathlib import Path

from ai_vastu.plan_schema import plan_document_json_schema

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "packages/contracts/schema/plan-document.schema.json"

expected = plan_document_json_schema()
actual = json.loads(TARGET.read_text(encoding="utf-8"))
if actual != expected:
    raise SystemExit(
        "Generated PlanDocument JSON Schema is stale. Run: python scripts/export-plan-schema.py"
    )
print("PlanDocument JSON Schema matches authoritative Pydantic models.")
