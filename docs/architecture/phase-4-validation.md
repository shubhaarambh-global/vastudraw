# Phase 4 Validation Gate

Phase 4 is accepted only when all inherited Phase 0–3 gates remain green and the new Vastu framework tests pass.

Required checks:

```text
pnpm validate
ruff check python apps/api tests
mypy
pytest
```

Expected Phase 4 invariants include:
- no production Vastu rule catalog exists;
- PlanDocument schema version remains 1.0.0;
- only FROZEN rules compile into production bundles;
- missing source provenance fails closed;
- contradictory equal-precedence hard rules fail closed;
- bundle hashes are deterministic across input order;
- missing facts become NOT_APPLICABLE rather than invented evidence;
- fact evaluation carries measured evidence;
- OR-Tools, ezdxf, and ReportLab are not introduced in this phase.


## Authoritative acceptance record

On the Windows/VS Code acceptance environment (Python 3.12, Node 24), the user confirmed:
- `pnpm validate` exited `0`;
- the chained Python gate `ruff check ...; mypy; pytest` exited `0`.

The two source-level corrections discovered during acceptance (Ruff SIM103 and regex escaping) are incorporated in this frozen archive.
