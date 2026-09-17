from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_vastu.vastu_spec import VastuSpecIntegrityError, load_vastu_spec_directory

ROOT = Path(__file__).resolve().parents[2]


def test_repository_v1_spec_is_valid_for_current_lifecycle() -> None:
    spec = load_vastu_spec_directory(ROOT / "docs/vastu/spec-v1.0")
    assert spec.verify_hash()

    lifecycle = spec.manifest.lifecycle.value
    assert lifecycle in {"DRAFT", "IN_REVIEW", "FROZEN"}

    if lifecycle == "DRAFT":
        assert spec.rule_records == ()
        assert spec.production_ready is False
    elif lifecycle == "FROZEN":
        assert spec.manifest.production_rule_count == len(spec.rule_records)
        assert spec.manifest.production_rule_count > 0
        assert len(spec.sources) > 0
        assert spec.production_ready is True
    else:
        assert spec.production_ready is False


def test_authoring_hash_is_deterministic() -> None:
    first = load_vastu_spec_directory(ROOT / "docs/vastu/spec-v1.0")
    second = load_vastu_spec_directory(ROOT / "docs/vastu/spec-v1.0")
    assert first.authoring_content_hash == second.authoring_content_hash


def test_manifest_rule_ids_must_match_rule_files(tmp_path: Path) -> None:
    spec_root = tmp_path / "spec"
    (spec_root / "rules").mkdir(parents=True)
    (spec_root / "sources.json").write_text("[]", encoding="utf-8")
    (spec_root / "manifest.json").write_text(
        json.dumps(
            {
                "spec_version": "1.0.0",
                "title": "Synthetic",
                "lifecycle": "DRAFT",
                "rule_ids": ["SYNTHETIC-RULE-001"],
                "production_rule_count": 0,
                "expected_rule_bundle_hash": None,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(VastuSpecIntegrityError, match="rule_ids"):
        load_vastu_spec_directory(spec_root)
