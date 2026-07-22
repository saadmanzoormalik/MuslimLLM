#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_app
docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop
