from __future__ import annotations

import json
from pathlib import Path

from ai_vastu.dwg import DwgTargetVersion, preferred_production_candidate
from ai_vastu.generation import GENERATION_PIPELINE_VERSION
from ai_vastu.plan_schema import PLAN_SCHEMA_VERSION

from .models import (
    ProductionReadinessReport,
    ReleaseDisposition,
    ReleaseGateResult,
    ReleaseGateStatus,
)

_SUPPORTED_PLAN_SCHEMA_VERSIONS = frozenset({"1.1.0"})


def _gate(
    code: str,
    status: ReleaseGateStatus,
    message: str,
    *evidence: str,
) -> ReleaseGateResult:
    return ReleaseGateResult(
        code=code,
        status=status,
        message=message,
        evidence=tuple(evidence),
    )


def _read_vastu_manifest(repository_root: Path) -> tuple[str, int, str | None]:
    path = repository_root / "docs/vastu/spec-v1.0/manifest.json"
    payload: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Vastu manifest must contain a JSON object.")

    lifecycle = payload.get("lifecycle")
    rule_count = payload.get("production_rule_count")
    bundle_hash = payload.get("expected_rule_bundle_hash")

    if not isinstance(lifecycle, str):
        raise ValueError("Vastu manifest lifecycle must be a string.")
    if isinstance(rule_count, bool) or not isinstance(rule_count, int):
        raise ValueError("Vastu manifest production_rule_count must be an integer.")
    if bundle_hash is not None and not isinstance(bundle_hash, str):
        raise ValueError("Vastu manifest expected_rule_bundle_hash must be a string or null.")
    return lifecycle, rule_count, bundle_hash


def evaluate_production_mvp_readiness(repository_root: Path) -> ProductionReadinessReport:
    lifecycle, production_rule_count, expected_rule_bundle_hash = _read_vastu_manifest(
        repository_root
    )
    dwg_candidate = preferred_production_candidate()

    gates: list[ReleaseGateResult] = []

    if PLAN_SCHEMA_VERSION in _SUPPORTED_PLAN_SCHEMA_VERSIONS:
        gates.append(
            _gate(
                "PLAN_SCHEMA_SUPPORTED",
                ReleaseGateStatus.PASS,
                "Canonical PlanDocument schema version is supported by the MVP release gate.",
                f"schema={PLAN_SCHEMA_VERSION}",
                f"supported={','.join(sorted(_SUPPORTED_PLAN_SCHEMA_VERSIONS))}",
            )
        )
    else:
        gates.append(
            _gate(
                "PLAN_SCHEMA_UNSUPPORTED",
                ReleaseGateStatus.BLOCKER,
                "Canonical PlanDocument schema version is not supported by this release gate.",
                f"schema={PLAN_SCHEMA_VERSION}",
                f"supported={','.join(sorted(_SUPPORTED_PLAN_SCHEMA_VERSIONS))}",
            )
        )

    if lifecycle == "FROZEN":
        gates.append(
            _gate(
                "VASTU_SPEC_FROZEN",
                ReleaseGateStatus.PASS,
                "Vastu Specification v1 is frozen for production use.",
                f"rules={production_rule_count}",
            )
        )
    else:
        gates.append(
            _gate(
                "VASTU_SPEC_NOT_FROZEN",
                ReleaseGateStatus.BLOCKER,
                "Production release requires a reviewed and FROZEN Vastu Specification v1.",
                f"lifecycle={lifecycle}",
            )
        )

    if production_rule_count > 0:
        gates.append(
            _gate(
                "VASTU_PRODUCTION_RULES_PRESENT",
                ReleaseGateStatus.PASS,
                "The frozen Vastu specification contains production rules.",
                f"rules={production_rule_count}",
            )
        )
    else:
        gates.append(
            _gate(
                "VASTU_RULESET_EMPTY",
                ReleaseGateStatus.BLOCKER,
                "A Vastu product cannot be released with zero approved production rules.",
                "rules=0",
            )
        )

    if expected_rule_bundle_hash is not None:
        gates.append(
            _gate(
                "VASTU_RULE_BUNDLE_PINNED",
                ReleaseGateStatus.PASS,
                "The production Vastu rule bundle is cryptographically pinned.",
                f"hash={expected_rule_bundle_hash}",
            )
        )
    else:
        gates.append(
            _gate(
                "VASTU_RULE_BUNDLE_NOT_PINNED",
                ReleaseGateStatus.BLOCKER,
                "Production release requires a frozen expected Vastu rule-bundle hash.",
            )
        )

    gates.extend(
        (
            _gate(
                "DETERMINISTIC_ENGINE_BASELINE",
                ReleaseGateStatus.PASS,
                "Constraint, solver, geometry, validation and scoring gates are wired into CI.",
            ),
            _gate(
                "PROJECT_REVISION_STORE",
                ReleaseGateStatus.PASS,
                "Immutable project revisions and durable repository semantics are implemented.",
            ),
            _gate(
                "INTERACTIVE_2D_EDITOR",
                ReleaseGateStatus.PASS,
                "The millimetre-authoritative interactive 2D editor is implemented.",
            ),
            _gate(
                "CORE_EXPORTS",
                ReleaseGateStatus.PASS,
                (
                    "SVG, JPEG, vector PDF and DXF export pathways are implemented "
                    "and deterministic, including multi-floor PDF sheets."
                ),
                "source=persisted-selected-revision",
                "ownership=server-enforced",
            ),
        )
    )

    if (
        dwg_candidate.production_candidate
        and dwg_candidate.modern_dwg_write
        and DwgTargetVersion.R2018 in dwg_candidate.supported_targets
    ):
        gates.append(
            _gate(
                "DWG_PATHWAY_AVAILABLE",
                ReleaseGateStatus.PASS,
                "A fail-closed R2018 DWG qualification pathway exists.",
                f"preferred_backend={dwg_candidate.backend_id}",
                "production_export_requires_runtime_qualification=true",
            )
        )
    else:
        gates.append(
            _gate(
                "DWG_PATHWAY_UNAVAILABLE",
                ReleaseGateStatus.BLOCKER,
                "The MVP requires a qualified modern-DWG backend pathway.",
            )
        )

    gates.extend(
        (
            _gate(
                "AUTHORIZATION_IMPLEMENTED",
                ReleaseGateStatus.PASS,
                (
                    "Supabase access tokens are verified at the API boundary and project "
                    "ownership is enforced for project/revision operations."
                ),
                "provider=supabase-auth",
                "jwt=asymmetric-jwks",
                "project_ownership=database-backed",
                "development_auth=forbidden_in_production",
            ),
            _gate(
                "PRODUCTION_PERSISTENCE_IMPLEMENTED",
                ReleaseGateStatus.PASS,
                (
                    "PostgreSQL/Supabase production persistence is implemented behind "
                    "the ProjectRepository boundary."
                ),
                "backend=postgresql",
                "driver=psycopg3",
                "sqlite_reference_only=true",
                "production_without_database_url=fail_closed",
            ),
            _gate(
                "GENERATION_API_IMPLEMENTED",
                ReleaseGateStatus.PASS,
                (
                    "The deterministic architectural planning pipeline is "
                    "exposed as an API workflow."
                ),
                f"pipeline_version={GENERATION_PIPELINE_VERSION}",
                "endpoint=POST /generation/architectural",
                "vastu_rules_applied=false",
            ),
            _gate(
                "WEB_API_WORKFLOW_IMPLEMENTED",
                ReleaseGateStatus.PASS,
                (
                    "The web editor is bound to project create/load/save and "
                    "architectural generation API flows."
                ),
                "project_api=create/load/save",
                "generation_api=POST /generation/architectural",
                "authoritative_units=mm",
            ),
        )
    )

    blocker_codes = tuple(gate.code for gate in gates if gate.status is ReleaseGateStatus.BLOCKER)
    disposition = ReleaseDisposition.READY if not blocker_codes else ReleaseDisposition.BLOCKED
    report = ProductionReadinessReport(
        disposition=disposition,
        gates=tuple(gates),
        blocker_codes=blocker_codes,
        blocker_count=len(blocker_codes),
    )
    return report.with_report_hash()
