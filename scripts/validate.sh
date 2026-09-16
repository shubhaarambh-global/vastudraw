#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

./scripts/check-policy.sh

if [ ! -d .venv ]; then
  echo ".venv not found. Run ./scripts/bootstrap-wsl.sh first."
  exit 1
fi

source .venv/bin/activate
ruff check python apps/api tests
mypy
pytest
pnpm validate

echo
printf '%s\n' "PHASE 7 ACCEPTANCE GATE: PASS"
