from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_vastu.production.staging_preflight import validate_staging_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted Phase 29E evidence.")
    parser.add_argument("evidence", type=Path)
    arguments = parser.parse_args()
    try:
        document = json.loads(arguments.evidence.read_text(encoding="utf-8"))
        validate_staging_evidence(document)
    except Exception:
        print('{"status":"FAIL","reason":"evidence_structure_invalid"}')
        return 1
    print(
        '{"status":"PASS_LOCAL","scope":"evidence_structure_only",'
        '"pass_live":false}'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
