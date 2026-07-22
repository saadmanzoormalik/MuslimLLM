#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$ROOT/.context-sync-run"
mkdir -p "$RUN_DIR"
if curl -fsS http://127.0.0.1:8200/health >/dev/null 2>&1; then
  echo "Demo AI Account already running"
  exit 0
fi
cd "$ROOT/services/mock-context-provider"
nohup "$ROOT/backend/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8200 >"$RUN_DIR/mock-provider.log" 2>&1 &
echo $! >"$RUN_DIR/mock-provider.pid"
echo "Started Demo AI Account"
