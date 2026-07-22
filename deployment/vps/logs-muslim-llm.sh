#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_app
if (( $# )); then
  docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail "${TAIL_LINES:-200}" -f "$@"
else
  docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail "${TAIL_LINES:-200}" -f
fi
