from pathlib import Path

from ai_vastu.release import ReleaseDisposition, evaluate_production_mvp_readiness

ROOT = Path(__file__).resolve().parents[1]
report = evaluate_production_mvp_readiness(ROOT)

print(
    "Production release readiness: "
    f"status={report.disposition.value}, blockers={report.blocker_count}, "
    f"hash={report.report_hash}"
)
for blocker in report.blocker_codes:
    print(f"BLOCKER: {blocker}")

if report.disposition is not ReleaseDisposition.READY:
    raise SystemExit(2)
