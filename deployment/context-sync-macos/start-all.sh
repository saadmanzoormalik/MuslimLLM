#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PG_PORT="${MUSLIM_LLM_POSTGRES_PORT:-5433}"
if ! pg_isready -h 127.0.0.1 -p "$PG_PORT" >/dev/null 2>&1; then
  if [[ -d "$ROOT/.postgres-data" ]]; then
    pg_ctl -D "$ROOT/.postgres-data" -l "$ROOT/.postgres-data/server.log" -o "-p $PG_PORT -k /tmp" start
  else
    echo "PostgreSQL is not running and $ROOT/.postgres-data is missing."
    exit 1
  fi
fi
"$ROOT/deployment/context-sync-macos/start-mock-provider.sh"
"$ROOT/deployment/context-sync-macos/start-auth-broker.sh"
"$ROOT/deployment/context-sync-macos/start-muslim-llm.sh"
for url in http://127.0.0.1:8200/health http://127.0.0.1:8100/v1/health http://127.0.0.1:8000/health http://127.0.0.1:3000/; do
  for _ in {1..30}; do
    curl -fsS "$url" >/dev/null 2>&1 && break
    sleep 0.5
  done
done
"$ROOT/deployment/context-sync-macos/verify-environment.sh"
echo ""
echo "Muslim LLM: http://127.0.0.1:3000"
echo "Transfer Context: http://127.0.0.1:3000/context-sync"
