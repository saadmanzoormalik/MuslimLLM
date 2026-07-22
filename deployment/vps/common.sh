#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MUSLIM_LLM_APP_DIR:-/opt/muslim-llm}"
COMPOSE_FILE="$APP_DIR/docker-compose.production.yml"
ENV_FILE="$APP_DIR/.env"
PROJECT_NAME="muslimllm"

compose() {
  docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

require_app() {
  [[ "$APP_DIR" == "/opt/muslim-llm" ]] || { echo "Unexpected application path: $APP_DIR" >&2; exit 1; }
  [[ -f "$COMPOSE_FILE" ]] || { echo "Missing $COMPOSE_FILE" >&2; exit 1; }
  [[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }
}

env_value() {
  local key="$1"
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -n 1
}

growthpilot_health() {
  [[ -d /opt/growthpilot ]] || { echo "GrowthPilot directory is missing" >&2; return 1; }
  (cd /opt/growthpilot && docker compose ps)
  curl -fsS --max-time 15 http://127.0.0.1:8000/health >/dev/null
  curl -fsSI --max-time 15 http://127.0.0.1:3000 >/dev/null
}

wait_for_url() {
  local url="$1" attempts="${2:-60}"
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 10 "$url" >/dev/null; then
      return 0
    fi
    sleep 3
  done
  echo "Timed out waiting for $url" >&2
  return 1
}
