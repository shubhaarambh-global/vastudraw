from __future__ import annotations

from datetime import datetime

from ai_vastu.vastu import RuleLifecycle, SourceRegistry, compile_rule_bundle

from .errors import VastuSpecApprovalError, VastuSpecIntegrityError
from .models import (
    LoadedVastuSpecification,
    ReviewStatus,
    SpecLifecycle,
    VastuSpecRelease,
)


def compile_production_release(
    spec: LoadedVastuSpecification,
    *,
    released_at: datetime,
) -> VastuSpecRelease:
    if spec.manifest.lifecycle is not SpecLifecycle.FROZEN:
        raise VastuSpecApprovalError("Only a FROZEN Vastu specification can be released.")
    if released_at.tzinfo is None:
        raise VastuSpecApprovalError("Release timestamp must be timezone-aware.")
    if not spec.rule_records:
        raise VastuSpecApprovalError("Production release requires at least one rule.")

    for record in spec.rule_records:
        if record.review.status is not ReviewStatus.APPROVED:
            raise VastuSpecApprovalError(
                f"Rule {record.rule.rule_id} is not APPROVED for production."
            )
        if record.rule.lifecycle is not RuleLifecycle.FROZEN:
            raise VastuSpecApprovalError(
                f"Rule {record.rule.rule_id} is not FROZEN for production."
            )

    registry = SourceRegistry(spec.sources)
    bundle = compile_rule_bundle(
        spec_version=spec.manifest.spec_version,
        rules=(item.rule for item in spec.rule_records),
        source_registry=registry,
        production=True,
    )
    expected_hash = spec.manifest.expected_rule_bundle_hash
    if bundle.content_hash != expected_hash:
        raise VastuSpecIntegrityError(
            "Compiled production rule bundle hash does not match frozen manifest."
        )

    provisional = VastuSpecRelease(
        spec_version="1.0.0",
        authoring_content_hash=spec.authoring_content_hash,
        rule_bundle_hash=bundle.content_hash,
        rule_count=len(bundle.rules),
        released_at=released_at,
        release_hash="0" * 64,
    )
    release = provisional.model_copy(update={"release_hash": provisional.compute_release_hash()})
    if not release.verify_hash():
        raise VastuSpecIntegrityError("Compiled release hash did not verify.")
    return release
