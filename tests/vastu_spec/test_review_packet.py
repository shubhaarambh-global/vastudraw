from __future__ import annotations

from ai_vastu.vastu import SourceRegistry
from ai_vastu.vastu_spec import build_review_packet

from .helpers import approved_synthetic_record, synthetic_source


def test_review_packet_resolves_sources_and_preserves_geometry_semantics() -> None:
    packet = build_review_packet(
        approved_synthetic_record(),
        source_registry=SourceRegistry((synthetic_source(),)),
    )
    assert packet["rule_id"] == "SYNTHETIC-RULE-001"
    assert packet["geometry_semantic"] == "AREA_OVERLAP_PERCENT"
    assert packet["review"]["status"] == "APPROVED"
    assert packet["resolved_sources"][0]["source_id"] == "SYNTHETIC-SOURCE-001"
