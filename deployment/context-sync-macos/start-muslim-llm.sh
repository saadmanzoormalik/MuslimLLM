#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$ROOT/.context-sync-run"
mkdir -p "$RUN_DIR"
if ! curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
  cd "$ROOT/backend"
  nohup env \
    DATABASE_URL="${DATABASE_URL:-postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm}" \
    AUTH_BROKER_URL=http://127.0.0.1:8100 \
    CONTEXT_SYNC_DEVICE_CALLBACK_BASE=http://127.0.0.1:8000/context-sync/device-callback \
    CONTEXT_SYNC_ALLOW_MOCK_PROVIDER=true \
    APP_ENVIRONMENT=development \
    .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$RUN_DIR/backend.log" 2>&1 &
  echo $! >"$RUN_DIR/backend.pid"
  echo "Started Muslim LLM backend"
fi
if ! curl -fsS http://127.0.0.1:3000/ >/dev/null 2>&1; then
  cd "$ROOT/frontend"
  nohup npm run dev -- --hostname 127.0.0.1 --port 3000 >"$RUN_DIR/frontend.log" 2>&1 &
  echo $! >"$RUN_DIR/frontend.pid"
  echo "Started Muslim LLM frontend"
fi
