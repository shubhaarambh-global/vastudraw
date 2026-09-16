from __future__ import annotations

import json
from pathlib import Path

from ai_vastu.vastu import SourceRegistry
from ai_vastu.vastu_spec import build_review_packet, load_vastu_spec_directory

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs/vastu/spec-v1.0"
OUT = SPEC_ROOT / "review-packets"

spec = load_vastu_spec_directory(SPEC_ROOT)
registry = SourceRegistry(spec.sources)
OUT.mkdir(parents=True, exist_ok=True)

expected_paths: set[Path] = set()
for record in spec.rule_records:
    packet = build_review_packet(record, source_registry=registry)
    path = OUT / f"{record.rule.rule_id}.json"
    expected_paths.add(path)
    path.write_text(
        json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

for stale in OUT.glob("*.json"):
    if stale not in expected_paths:
        stale.unlink()

print(
    "Vastu review packets generated: "
    f"count={len(expected_paths)}, authoring_hash={spec.authoring_content_hash}"
)
