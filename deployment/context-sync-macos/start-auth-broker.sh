#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$ROOT/.context-sync-run"
mkdir -p "$RUN_DIR"
if curl -fsS http://127.0.0.1:8100/v1/health >/dev/null 2>&1; then
  echo "Context Authorization Broker already running"
  exit 0
fi
cd "$ROOT/services/context-auth-broker"
nohup env \
  AUTH_BROKER_DATABASE_URL="${AUTH_BROKER_DATABASE_URL:-postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm}" \
  AUTH_BROKER_PUBLIC_URL="${AUTH_BROKER_PUBLIC_URL:-http://127.0.0.1:8100}" \
  AUTH_BROKER_ENCRYPTION_KEY="${AUTH_BROKER_ENCRYPTION_KEY:-development-broker-key-change-me}" \
  AUTH_BROKER_ENVIRONMENT=development \
  MOCK_CONTEXT_PROVIDER_URL=http://127.0.0.1:8200 \
  CONTEXT_SYNC_ALLOW_MOCK_PROVIDER=true \
  "$ROOT/backend/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8100 >"$RUN_DIR/auth-broker.log" 2>&1 &
echo $! >"$RUN_DIR/auth-broker.pid"
echo "Started Context Authorization Broker"
