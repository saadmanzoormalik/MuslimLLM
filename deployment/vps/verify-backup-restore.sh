#!/usr/bin/env bash
set -Eeuo pipefail

backup_dir="${1:-}"
[[ -d "$backup_dir" && -f "$backup_dir/postgres.dump" ]] || { echo "Usage: $0 BACKUP_DIRECTORY" >&2; exit 1; }
(cd "$backup_dir" && sha256sum -c SHA256SUMS)

suffix="$(date -u +%Y%m%d%H%M%S)"
container="muslimllm-restore-test-$suffix"
volume="muslimllm-restore-test-$suffix"
password="$(openssl rand -hex 24)"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker volume create "$volume" >/dev/null
docker run -d --name "$container" \
  -e POSTGRES_DB=muslim_llm_restore_test \
  -e POSTGRES_USER=restore_test \
  -e POSTGRES_PASSWORD="$password" \
  -v "$volume:/var/lib/postgresql/data" \
  pgvector/pgvector:0.8.0-pg16 >/dev/null

for _ in {1..30}; do
  docker exec "$container" pg_isready -U restore_test -d muslim_llm_restore_test >/dev/null 2>&1 && break
  sleep 2
done
docker exec "$container" pg_isready -U restore_test -d muslim_llm_restore_test >/dev/null
docker exec -i "$container" pg_restore -U restore_test -d muslim_llm_restore_test --no-owner --no-privileges < "$backup_dir/postgres.dump"
docker exec "$container" psql -U restore_test -d muslim_llm_restore_test -Atc \
  "select extname from pg_extension where extname='vector'; select count(*) from information_schema.tables where table_schema='public';" \
  | grep -q vector
echo "Isolated Muslim LLM restore verification passed"
