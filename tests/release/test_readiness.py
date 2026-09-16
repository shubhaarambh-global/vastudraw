from pathlib import Path

from ai_vastu.release import (
    ReleaseDisposition,
    ReleaseGateStatus,
    evaluate_production_mvp_readiness,
)

ROOT = Path(__file__).resolve().parents[2]


def test_current_public_mvp_is_ready_after_phase20b_freeze() -> None:
    report = evaluate_production_mvp_readiness(ROOT)
    assert report.disposition is ReleaseDisposition.READY
    assert report.blocker_codes == ()
    assert report.blocker_count == 0


def test_readiness_report_is_deterministic_and_hashed() -> None:
    first = evaluate_production_mvp_readiness(ROOT)
    second = evaluate_production_mvp_readiness(ROOT)
    assert first == second
    assert first.report_hash is not None
    assert first.report_hash == first.compute_report_hash()


def test_dwg_pathway_is_not_misrepresented_as_live_export() -> None:
    report = evaluate_production_mvp_readiness(ROOT)
    gate = next(item for item in report.gates if item.code == "DWG_PATHWAY_AVAILABLE")
    assert gate.status is ReleaseGateStatus.PASS
    assert "production_export_requires_runtime_qualification=true" in gate.evidence
