#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_DIR="$ROOT/.context-sync-run"
for name in frontend backend auth-broker mock-provider; do
  pid_file="$RUN_DIR/$name.pid"
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    kill "$pid" >/dev/null 2>&1 || true
    rm -f "$pid_file"
    echo "Stopped $name"
  fi
done
