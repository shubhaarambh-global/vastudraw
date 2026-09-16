#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for f in \
  README.md \
  THIRD_PARTY.md \
  docs/architecture/phase-7-freeze.md \
  docs/architecture/phase-7-validation.md \
  docs/adr/ADR-025-cp-sat-rectangular-planner.md \
  docs/adr/ADR-026-solver-lattice-and-reproducibility.md \
  docs/solver/phase-7-contract.md \
  packages/contracts/schema/plan-document.schema.json; do
  test -s "$f" || { echo "Missing/empty required file: $f"; exit 1; }
done

test ! -e python/ai_vastu/vastu/rules.json || {
  echo "Unsourced production Vastu rule catalog must not be shipped."
  exit 1
}

grep -q 'ortools==9.15.6755' pyproject.toml || {
  echo "Phase 7 must pin OR-Tools 9.15.6755."
  exit 1
}

echo "Phase 7 repository policy checks passed."
