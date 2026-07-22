#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$ROOT/.context-sync-run"
STORAGE_DIR="$ROOT/.context-sync-openai"
DB_URL="${DATABASE_URL:-postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm}"
mkdir -p "$RUN_DIR" "$STORAGE_DIR"

if ! pg_isready -d "$DB_URL" >/dev/null 2>&1; then
  if [ -d "$ROOT/.postgres-data" ]; then
    pg_ctl -D "$ROOT/.postgres-data" -l "$RUN_DIR/postgres.log" -o "-p 5433 -k /tmp" start
  else
    echo "PostgreSQL is not ready."
    exit 1
  fi
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama is not ready on 127.0.0.1:11434."
  exit 1
fi

probe="$STORAGE_DIR/.write-test"
if ! touch "$probe" 2>/dev/null; then
  echo "Context Sync storage is not writable: $STORAGE_DIR"
  exit 1
fi
rm -f "$probe"

available_kb="$(df -Pk "$STORAGE_DIR" | awk 'NR==2 {print $4}')"
if [ "${available_kb:-0}" -lt 2097152 ]; then
  echo "At least 2 GB of free disk space is required."
  exit 1
fi

if ! curl -fsS http://127.0.0.1:8000/context-sync/openai/status >/dev/null 2>&1; then
  backend_pids="$(lsof -ti tcp:8000 2>/dev/null || true)"
  if [ -n "$backend_pids" ]; then echo "$backend_pids" | xargs kill; sleep 1; fi
  cd "$ROOT/backend"
  nohup env \
    DATABASE_URL="$DB_URL" \
    ENABLE_OPENAI_CONTEXT_SYNC=true \
    CONTEXT_SYNC_OPENAI_VERIFIED_HISTORY="${CONTEXT_SYNC_OPENAI_VERIFIED_HISTORY:-false}" \
    CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH="${CONTEXT_SYNC_OPENAI_APPROVED_EXPORT_PATH:-}" \
    CONTEXT_SYNC_LOCAL_PROCESSING=true \
    CONTEXT_SYNC_ALLOW_CLOUD_CONTENT_UPLOAD=false \
    CONTEXT_SYNC_LOCAL_FILES_ONLY=true \
    LLM_API_BASE="${LLM_API_BASE:-http://127.0.0.1:11434/v1}" \
    LLM_MODEL="${LLM_MODEL:-qwen3:8b}" \
    .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$RUN_DIR/backend.log" 2>&1 &
  echo $! >"$RUN_DIR/backend.pid"
fi

if ! curl -fsS http://127.0.0.1:3000/context-sync/openai >/dev/null 2>&1; then
  frontend_pids="$(lsof -ti tcp:3000 2>/dev/null || true)"
  if [ -n "$frontend_pids" ]; then echo "$frontend_pids" | xargs kill; sleep 1; fi
  cd "$ROOT/frontend"
  nohup env NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 \
    npm run dev -- --hostname 127.0.0.1 --port 3000 >"$RUN_DIR/frontend.log" 2>&1 &
  echo $! >"$RUN_DIR/frontend.pid"
fi

for _ in {1..60}; do
  if curl -fsS http://127.0.0.1:8000/context-sync/openai/status >/dev/null 2>&1 && curl -fsS http://127.0.0.1:3000/context-sync/openai >/dev/null 2>&1; then
    echo "Muslim LLM: http://127.0.0.1:3000/"
    echo "LLM Context Sync: http://127.0.0.1:3000/context-sync/openai"
    echo "Durable PostgreSQL worker: ready"
    exit 0
  fi
  sleep 1
done

echo "Startup timed out. Check $RUN_DIR/backend.log and $RUN_DIR/frontend.log."
exit 1
