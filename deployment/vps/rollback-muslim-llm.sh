#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_app
target="${1:-$(cat "$APP_DIR/deployment/state/previous-version" 2>/dev/null || true)}"
[[ -n "$target" ]] || { echo "No previous Muslim LLM version is recorded" >&2; exit 1; }
docker image inspect "muslimllm-backend:$target" >/dev/null
docker image inspect "muslimllm-frontend:$target" >/dev/null
sed -i "s/^MUSLIM_LLM_IMAGE_TAG=.*/MUSLIM_LLM_IMAGE_TAG=$target/" "$ENV_FILE"
sed -i "s/^APP_VERSION=.*/APP_VERSION=$target/" "$ENV_FILE"
docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --no-build
wait_for_url http://127.0.0.1:8200/health 60
wait_for_url http://127.0.0.1:3200 40
echo "Rolled back only Muslim LLM to $target"
