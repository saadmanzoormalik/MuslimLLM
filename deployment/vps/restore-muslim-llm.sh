#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_app
backup_dir="${1:-}"
confirmation="${2:-}"
[[ -d "$backup_dir" && -f "$backup_dir/postgres.dump" ]] || { echo "Usage: $0 BACKUP_DIRECTORY --confirm" >&2; exit 1; }
[[ "$confirmation" == "--confirm" ]] || { echo "Restore requires --confirm" >&2; exit 1; }
(cd "$backup_dir" && sha256sum -c SHA256SUMS)

POSTGRES_USER="$(env_value POSTGRES_USER)"
POSTGRES_DB="$(env_value POSTGRES_DB)"
docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop frontend backend worker
docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < "$backup_dir/postgres.dump"

for item in documents:muslimllm-documents context:muslimllm-context-imports updates:muslimllm-updates; do
  archive="${item%%:*}"
  volume="${item##*:}"
  [[ -f "$backup_dir/$archive.tar.gz" ]] || continue
  docker run --rm -v "$volume:/data" -v "$backup_dir:/backup:ro" alpine:3.21 \
    sh -ec "find /data -mindepth 1 -delete; tar -xzf /backup/$archive.tar.gz -C /data; chown -R 10001:10001 /data"
done

docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d
wait_for_url http://127.0.0.1:8200/health 60
echo "Muslim LLM restore completed"
