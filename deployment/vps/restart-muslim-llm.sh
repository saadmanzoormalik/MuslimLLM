#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_app
docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" restart backend worker frontend
wait_for_url http://127.0.0.1:8200/health 40
wait_for_url http://127.0.0.1:3200 30
