from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_vastu.vastu import SourceRegistry, compile_rule_bundle
from ai_vastu.vastu_spec import (
    LoadedVastuSpecification,
    SpecLifecycle,
    VastuSpecApprovalError,
    VastuSpecManifest,
    compile_production_release,
)

from .helpers import approved_synthetic_record, synthetic_source


def _frozen_synthetic_spec() -> LoadedVastuSpecification:
    record = approved_synthetic_record()
    source = synthetic_source()
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        rules=(record.rule,),
        source_registry=SourceRegistry((source,)),
        production=True,
    )
    manifest = VastuSpecManifest(
        spec_version="1.0.0",
        title="Synthetic frozen spec",
        lifecycle=SpecLifecycle.FROZEN,
        rule_ids=(record.rule.rule_id,),
        production_rule_count=1,
        expected_rule_bundle_hash=bundle.content_hash,
    )
    provisional = LoadedVastuSpecification(
        manifest=manifest,
        sources=(source,),
        rule_records=(record,),
        authoring_content_hash="0" * 64,
    )
    return provisional.model_copy(
        update={"authoring_content_hash": provisional.compute_authoring_content_hash()}
    )


def test_frozen_approved_spec_compiles_reproducible_release() -> None:
    spec = _frozen_synthetic_spec()
    released_at = datetime(2026, 1, 2, tzinfo=UTC)
    first = compile_production_release(spec, released_at=released_at)
    second = compile_production_release(spec, released_at=released_at)
    assert first == second
    assert first.rule_count == 1
    assert first.rule_bundle_hash == spec.manifest.expected_rule_bundle_hash
    assert first.verify_hash()


def test_draft_repository_spec_cannot_be_released() -> None:
    root_spec = LoadedVastuSpecification(
        manifest=VastuSpecManifest(
            spec_version="1.0.0",
            title="Draft",
            lifecycle=SpecLifecycle.DRAFT,
        ),
        sources=(),
        rule_records=(),
        authoring_content_hash="0" * 64,
    )
    root_spec = root_spec.model_copy(
        update={"authoring_content_hash": root_spec.compute_authoring_content_hash()}
    )
    with pytest.raises(VastuSpecApprovalError, match="FROZEN"):
        compile_production_release(
            root_spec,
            released_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
