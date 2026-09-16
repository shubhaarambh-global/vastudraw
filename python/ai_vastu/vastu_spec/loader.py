from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ai_vastu.vastu import SourceRecord

from .errors import VastuSpecIntegrityError, VastuSpecLoadError
from .models import LoadedVastuSpecification, RuleAuthoringRecord, VastuSpecManifest


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VastuSpecLoadError(f"Missing Vastu specification file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VastuSpecLoadError(f"Invalid JSON in Vastu specification file: {path}") from exc


def _load_sources(path: Path) -> tuple[SourceRecord, ...]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        raise VastuSpecLoadError("sources.json must contain a JSON array.")
    try:
        records = tuple(
            SourceRecord.model_validate_json(json.dumps(item)) for item in payload
        )
    except ValidationError as exc:
        raise VastuSpecLoadError("sources.json contains an invalid source record.") from exc
    ordered = tuple(sorted(records, key=lambda item: item.source_id))
    ids = [item.source_id for item in ordered]
    if len(ids) != len(set(ids)):
        raise VastuSpecIntegrityError("sources.json contains duplicate source_id values.")
    return ordered


def _load_rule_records(directory: Path) -> tuple[RuleAuthoringRecord, ...]:
    if not directory.is_dir():
        raise VastuSpecLoadError(f"Missing Vastu rule directory: {directory}")
    records: list[RuleAuthoringRecord] = []
    for path in sorted(directory.glob("*.json")):
        try:
            records.append(
                RuleAuthoringRecord.model_validate_json(json.dumps(_read_json(path)))
            )
        except ValidationError as exc:
            raise VastuSpecLoadError(f"Invalid rule authoring record: {path.name}") from exc
    ordered = tuple(sorted(records, key=lambda item: item.rule.rule_id))
    ids = [item.rule.rule_id for item in ordered]
    if len(ids) != len(set(ids)):
        raise VastuSpecIntegrityError("Rule directory contains duplicate rule_id values.")
    return ordered


def _canonical_authoring_hash(
    *,
    manifest: VastuSpecManifest,
    sources: tuple[SourceRecord, ...],
    rule_records: tuple[RuleAuthoringRecord, ...],
) -> str:
    payload = {
        "manifest": manifest.model_dump(mode="json"),
        "sources": [item.model_dump(mode="json") for item in sources],
        "rule_records": [item.model_dump(mode="json") for item in rule_records],
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_vastu_spec_directory(root: Path) -> LoadedVastuSpecification:
    try:
        manifest = VastuSpecManifest.model_validate_json(
            json.dumps(_read_json(root / "manifest.json"))
        )
    except ValidationError as exc:
        raise VastuSpecLoadError("manifest.json does not satisfy the Vastu spec schema.") from exc
    sources = _load_sources(root / "sources.json")
    rule_records = _load_rule_records(root / "rules")

    actual_rule_ids = tuple(item.rule.rule_id for item in rule_records)
    if actual_rule_ids != manifest.rule_ids:
        raise VastuSpecIntegrityError(
            "Manifest rule_ids do not exactly match sorted authoring rule files."
        )
    for record in rule_records:
        if record.rule.spec_version != manifest.spec_version:
            raise VastuSpecIntegrityError(
                f"Rule {record.rule.rule_id} spec_version does not match manifest."
            )

    content_hash = _canonical_authoring_hash(
        manifest=manifest,
        sources=sources,
        rule_records=rule_records,
    )
    loaded = LoadedVastuSpecification(
        manifest=manifest,
        sources=sources,
        rule_records=rule_records,
        authoring_content_hash=content_hash,
    )
    if not loaded.verify_hash():
        raise VastuSpecIntegrityError("Loaded Vastu specification hash did not verify.")
    return loaded
