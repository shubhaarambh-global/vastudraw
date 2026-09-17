from __future__ import annotations

import json
from pathlib import Path


def test_phase26b_policy_never_hard_rules_vastu() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "docs/vastu/spec-v2-draft/seed-rule-catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    assert catalog["hard_constraints_allowed"] is False
    assert all(rule["hard_constraint"] is False for rule in catalog["rules"])

    service = (root / "python/ai_vastu/vastu_reasoning/service.py").read_text(encoding="utf-8")
    evaluator = (root / "python/ai_vastu/vastu_reasoning/evaluator.py").read_text(encoding="utf-8")
    assert "hard_constraint" not in evaluator
    assert "VASTU_FORWARD: (3000, 7000)" in service
    assert "PRACTICAL: (7000, 3000)" in service
