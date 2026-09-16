from pathlib import Path

from ai_vastu.release import ReleaseDisposition, evaluate_production_mvp_readiness

ROOT = Path(__file__).resolve().parents[1]

report = evaluate_production_mvp_readiness(ROOT)
if report.disposition is not ReleaseDisposition.READY:
    raise SystemExit(
        "Phase 20B expected the production-MVP release gate to be READY."
    )
if report.blocker_codes != ():
    raise SystemExit(
        "Unexpected production blocker set: " + ",".join(report.blocker_codes)
    )
if report.report_hash is None:
    raise SystemExit("Readiness report hash was not produced.")

print(
    "Production MVP gate deterministic: "
    f"status={report.disposition.value}, blockers={report.blocker_count}, "
    f"hash={report.report_hash}"
)
