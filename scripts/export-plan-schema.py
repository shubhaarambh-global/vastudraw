from pathlib import Path

from ai_vastu.plan_schema import write_plan_document_json_schema

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "packages/contracts/schema/plan-document.schema.json"
write_plan_document_json_schema(TARGET)
print(f"Wrote {TARGET.relative_to(ROOT)}")
