from __future__ import annotations

import json
import os

from ai_vastu.production.staging_preflight import evaluate_staging_preflight


def main() -> int:
    try:
        report = evaluate_staging_preflight(os.environ)
    except Exception:
        report = {
            "schema_version": 1,
            "mode": "offline_no_egress",
            "preflight_status": "FAIL",
            "failures": ["internal_preflight_error"],
            "pass_live": False,
            "network_calls_performed": False,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    status = report["preflight_status"]
    if status == "PASS_LOCAL":
        return 0
    if status in {"BLOCKED_CREDENTIALS", "BLOCKED_HUMAN_ACTION"}:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

