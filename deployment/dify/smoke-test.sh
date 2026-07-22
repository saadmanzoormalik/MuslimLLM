#!/usr/bin/env bash
set -Eeuo pipefail

base_url="${DIFY_BASE_URL:-http://127.0.0.1:3300}"

curl -fsS --max-time 20 "$base_url/console/api/setup" | grep -Eq 'not_started|finished'
curl -fsS --max-time 20 "$base_url/console/api/system-features" >/dev/null

bound_ports="$(docker ps --format '{{.Names}}|{{.Ports}}' | grep '^muslim-knowledge-fabric-' || true)"
if grep -Eq '0\.0\.0\.0:3300|\[::\]:3300|:5003->' <<<"$bound_ports"; then
  echo "Dify exposed an unexpected public control-plane port" >&2
  exit 1
fi

echo "Dify control plane is healthy and loopback-only"
