#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"
cd "$APP_DIR"

mkdir -p deployment/logs deployment/state deployment/backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="deployment/logs/deploy-$timestamp.log"
exec > >(tee -a "$log_file") 2>&1

echo "[$timestamp] Muslim LLM isolated deployment preflight"
command -v docker >/dev/null
docker info >/dev/null
docker compose version
[[ -d /opt/growthpilot ]] || { echo "GrowthPilot is missing; stopping"; exit 1; }
[[ "$APP_DIR" == "/opt/muslim-llm" ]] || { echo "Unexpected application path"; exit 1; }

echo "--- host ---"
date -u
hostname
uname -a
docker ps
docker compose ls
ss -lntp || true
df -h
free -h
nproc

echo "--- GrowthPilot preflight ---"
growthpilot_health
(cd /opt/growthpilot && docker compose ps -q | sort) > deployment/state/growthpilot-pre.ids
docker volume ls --format '{{.Name}}' | grep -i growthpilot | sort > deployment/state/growthpilot-pre.volumes || true

existing_ids="$(compose ps -q 2>/dev/null || true)"
if [[ -z "$existing_ids" ]]; then
  if ss -H -ltn | awk '{print $4}' | grep -Eq '(:|\])3200$|(:|\])8200$'; then
    echo "Port 3200 or 8200 is already occupied; stopping" >&2
    exit 1
  fi
fi

mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
disk_kb="$(df -Pk /opt | awk 'NR==2 {print $4}')"
cpu_count="$(nproc)"
(( mem_kb >= 7000000 )) || { echo "At least 7 GB RAM is required for the local model stack" >&2; exit 1; }
(( disk_kb >= 20000000 )) || { echo "At least 20 GB free disk is required" >&2; exit 1; }
(( cpu_count >= 2 )) || { echo "At least 2 CPU cores are required" >&2; exit 1; }

if [[ ! -f .env ]]; then
  "$SCRIPT_DIR/generate-production-env.sh"
fi
require_app
[[ "$(stat -c '%a' .env)" == "600" ]] || chmod 600 .env

for key in POSTGRES_PASSWORD DATABASE_URL SECRET_KEY AUTH_SECRET_KEY ENCRYPTION_KEY CONTEXT_SYNC_TOKEN_KEY; do
  value="$(sed -n "s/^${key}=//p" .env)"
  [[ -n "$value" ]] || { echo "Required production value $key is empty" >&2; exit 1; }
done

previous_tag="$(sed -n 's/^MUSLIM_LLM_IMAGE_TAG=//p' .env)"
new_tag="${1:-$(date -u +%Y.%m.%d-%H%M%S)}"
printf '%s\n' "$previous_tag" > deployment/state/previous-version
sed -i "s/^MUSLIM_LLM_IMAGE_TAG=.*/MUSLIM_LLM_IMAGE_TAG=$new_tag/" .env
sed -i "s/^APP_VERSION=.*/APP_VERSION=$new_tag/" .env

rollback_on_failure() {
  code=$?
  if (( code != 0 )); then
    echo "Deployment failed; preserving data and attempting Muslim LLM-only rollback"
    if [[ -n "$previous_tag" ]] && docker image inspect "muslimllm-backend:$previous_tag" >/dev/null 2>&1; then
      "$SCRIPT_DIR/rollback-muslim-llm.sh" "$previous_tag" || true
    fi
  fi
  exit "$code"
}
trap rollback_on_failure ERR

echo "--- validate and build ---"
docker compose -p muslimllm --env-file .env -f docker-compose.production.yml config --quiet
docker compose -p muslimllm --env-file .env -f docker-compose.production.yml build --pull
docker compose -p muslimllm --env-file .env -f docker-compose.production.yml up -d

wait_for_url http://127.0.0.1:8200/health 80
wait_for_url http://127.0.0.1:3200 50
PUBLIC_FRONTEND_URL=http://127.0.0.1:3200 PUBLIC_BACKEND_URL=http://127.0.0.1:8200 "$SCRIPT_DIR/smoke-test-muslim-llm.sh"

echo "--- GrowthPilot postflight ---"
growthpilot_health
(cd /opt/growthpilot && docker compose ps -q | sort) > deployment/state/growthpilot-post.ids
docker volume ls --format '{{.Name}}' | grep -i growthpilot | sort > deployment/state/growthpilot-post.volumes || true
diff -u deployment/state/growthpilot-pre.ids deployment/state/growthpilot-post.ids
diff -u deployment/state/growthpilot-pre.volumes deployment/state/growthpilot-post.volumes

trap - ERR
printf '%s\n' "$new_tag" > deployment/state/current-version
docker compose -p muslimllm --env-file .env -f docker-compose.production.yml ps
echo "Frontend: http://148.113.203.232:3200"
echo "Backend:  http://148.113.203.232:8200"
echo "Health:   http://148.113.203.232:8200/health"
echo "Status: Internal test pending external browser and restore verification"
