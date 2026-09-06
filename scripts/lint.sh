#!/usr/bin/env bash
# Lint Python (ruff) and the React UI (eslint + tsc). Used by `git push` via .githooks/pre-push.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

fail() {
  echo "lint: $*" >&2
  exit 1
}

echo "==> Python (ruff)"
RUFF=""
if [[ -x "$ROOT/.venv/bin/ruff" ]]; then
  RUFF="$ROOT/.venv/bin/ruff"
elif command -v ruff >/dev/null 2>&1; then
  RUFF="$(command -v ruff)"
elif python3 -c "import ruff" >/dev/null 2>&1; then
  RUFF="python3 -m ruff"
else
  fail "ruff is not installed. From the repo root: python3 -m pip install -r requirements-dev.txt"
fi
# shellcheck disable=SC2086
$RUFF check app

echo "==> Frontend (eslint + tsc)"
if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  fail "frontend/node_modules is missing. From frontend/: npm install"
fi
if [[ ! -x "$ROOT/frontend/node_modules/.bin/eslint" ]]; then
  fail "eslint is not installed. From frontend/: npm install"
fi
(cd "$ROOT/frontend" && npm run lint)

echo "lint: ok"
