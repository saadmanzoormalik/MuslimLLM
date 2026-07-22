#!/usr/bin/env bash
set -Eeuo pipefail

RUNTIME_DIR="${DIFY_RUNTIME_DIR:-/opt/muslim-llm/dify-runtime}"
PROJECT_NAME="muslim-knowledge-fabric"
OVERRIDE_FILE="${DIFY_OVERRIDE_FILE:-/opt/muslim-llm/deployment/dify/docker-compose.override.yml}"

[[ "$RUNTIME_DIR" == "/opt/muslim-llm/dify-runtime" ]] || {
  echo "Unexpected Dify runtime path: $RUNTIME_DIR" >&2
  exit 1
}
[[ -f "$RUNTIME_DIR/docker-compose.yaml" ]] || {
  echo "Missing official Dify Compose file" >&2
  exit 1
}
[[ -f "$OVERRIDE_FILE" ]] || {
  echo "Missing Muslim Knowledge Fabric override" >&2
  exit 1
}

compose() {
  docker compose \
    -p "$PROJECT_NAME" \
    --env-file "$RUNTIME_DIR/.env" \
    -f "$RUNTIME_DIR/docker-compose.yaml" \
    -f "$OVERRIDE_FILE" \
    "$@"
}

case "${1:-status}" in
  up)
    docker network inspect muslimllm-fabric >/dev/null
    compose config --quiet
    compose up -d
    ;;
  down)
    compose down
    ;;
  restart)
    compose restart
    ;;
  logs)
    compose logs --tail=200 "${2:-api}"
    ;;
  status)
    compose ps
    ;;
  *)
    echo "Usage: $0 {up|down|restart|logs [service]|status}" >&2
    exit 2
    ;;
esac
