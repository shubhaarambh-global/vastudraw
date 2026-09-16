from __future__ import annotations

from typing import Any

from ai_vastu.vastu import SourceRegistry

from .models import RuleAuthoringRecord


def build_review_packet(
    record: RuleAuthoringRecord,
    *,
    source_registry: SourceRegistry,
) -> dict[str, Any]:
    sources = [
        source_registry.require(reference).model_dump(mode="json")
        for reference in record.rule.source_refs
    ]
    return {
        "rule_id": record.rule.rule_id,
        "rule_version": record.rule.rule_version,
        "spec_version": record.rule.spec_version,
        "normalized_statement": record.normalized_statement,
        "interpretation_notes": record.interpretation_notes,
        "geometry_semantic": record.rule.geometry_semantic.value,
        "classification": record.rule.classification.value,
        "severity": record.rule.severity.value,
        "weight": record.rule.weight,
        "precedence": record.rule.precedence,
        "source_references": [item.model_dump(mode="json") for item in record.rule.source_refs],
        "resolved_sources": sources,
        "review": record.review.model_dump(mode="json"),
    }
