#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v node >/dev/null || { echo "Node.js 24+ is required."; exit 1; }
command -v pnpm >/dev/null || { echo "pnpm is required. Try: corepack enable"; exit 1; }
command -v python3 >/dev/null || { echo "Python 3.12+ is required."; exit 1; }

python3 - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ required; found {sys.version.split()[0]}")
PY

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -e '.[dev]'
pnpm install
pnpm contracts:generate

echo "Bootstrap complete. Run: ./scripts/validate.sh"
