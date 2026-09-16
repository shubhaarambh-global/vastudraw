from __future__ import annotations

import json
from pathlib import Path

from .models import PlanDocument


def plan_document_json_schema() -> dict[str, object]:
    return PlanDocument.model_json_schema(mode="validation")


def write_plan_document_json_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = plan_document_json_schema()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
