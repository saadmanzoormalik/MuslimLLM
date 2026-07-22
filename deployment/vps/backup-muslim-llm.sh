#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
require_app
cd "$APP_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="deployment/backups/$timestamp"
mkdir -p "$backup_dir"

POSTGRES_USER="$(env_value POSTGRES_USER)"
POSTGRES_DB="$(env_value POSTGRES_DB)"
BACKUP_RETENTION_DAYS="$(env_value BACKUP_RETENTION_DAYS)"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
docker compose -p muslimllm --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$backup_dir/postgres.dump"

for item in documents:muslimllm-documents context:muslimllm-context-imports updates:muslimllm-updates; do
  archive="${item%%:*}"
  volume="${item##*:}"
  docker run --rm --user "$(id -u):$(id -g)" \
    -v "$volume:/data:ro" -v "$APP_DIR/$backup_dir:/backup" alpine:3.21 \
    tar -czf "/backup/$archive.tar.gz" -C /data .
done

cp version.json "$backup_dir/version.json"
grep -Ev '(PASSWORD|SECRET|PRIVATE_KEY|API_KEY|TOKEN_KEY)=' "$ENV_FILE" > "$backup_dir/config.public.env"
(cd "$backup_dir" && sha256sum postgres.dump ./*.tar.gz version.json config.public.env > SHA256SUMS)
chmod -R go-rwx "$backup_dir"
find deployment/backups -mindepth 1 -maxdepth 1 -type d -mtime "+$BACKUP_RETENTION_DAYS" -exec rm -rf -- {} +
echo "$APP_DIR/$backup_dir"
