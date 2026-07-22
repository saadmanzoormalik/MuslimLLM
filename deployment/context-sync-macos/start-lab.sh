#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$ROOT/.context-sync-run"
DB_URL="${DATABASE_URL:-postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm}"
mkdir -p "$RUN_DIR"

if ! pg_isready -d "$DB_URL" >/dev/null 2>&1; then
  if [ -d "$ROOT/.postgres-data" ]; then
    pg_ctl -D "$ROOT/.postgres-data" -l "$RUN_DIR/postgres.log" -o "-p 5433 -k /tmp" start
  else
    echo "PostgreSQL is not ready and .postgres-data was not found."
    exit 1
  fi
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama is not ready on 127.0.0.1:11434. Start Ollama, then rerun this command."
  exit 1
fi

for port in 8000 3000; do
  pids="$(lsof -ti tcp:$port 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill
  fi
done
sleep 1

cd "$ROOT/backend"
nohup env \
  DATABASE_URL="$DB_URL" \
  ENABLE_CONTEXT_SYNC_LAB=true \
  CONTEXT_SYNC_ENV=lab \
  CONTEXT_SYNC_LAB_DATABASE_SCHEMA=context_sync_lab \
  CONTEXT_SYNC_LAB_STORAGE_PATH="$ROOT/.context-sync-lab" \
  CONTEXT_SYNC_LOCAL_PROCESSING=true \
  CONTEXT_SYNC_ALLOW_CLOUD_CONTENT_UPLOAD=false \
  CONTEXT_SYNC_LOCAL_FILES_ONLY=true \
  LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:11434/v1}" \
  LLM_MODEL="${LLM_MODEL:-qwen3:8b}" \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$RUN_DIR/backend.log" 2>&1 &
echo $! >"$RUN_DIR/backend.pid"

cd "$ROOT/frontend"
nohup env NEXT_PUBLIC_ENABLE_CONTEXT_SYNC_LAB=true NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 \
  npm run dev -- --hostname 127.0.0.1 --port 3000 >"$RUN_DIR/frontend.log" 2>&1 &
echo $! >"$RUN_DIR/frontend.pid"

for _ in {1..40}; do
  if curl -fsS http://127.0.0.1:8000/context-sync-lab/providers >/dev/null 2>&1 && curl -fsS http://127.0.0.1:3000/context-sync-lab >/dev/null 2>&1; then
    echo "Context Sync Lab is ready: http://127.0.0.1:3000/context-sync-lab"
    echo "Worker: embedded durable PostgreSQL-backed worker"
    exit 0
  fi
  sleep 1
done

echo "Lab startup timed out. Check $RUN_DIR/backend.log and $RUN_DIR/frontend.log."
exit 1
