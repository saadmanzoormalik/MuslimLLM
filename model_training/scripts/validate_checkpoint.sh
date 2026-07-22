#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "$root/.venv/bin/python" "$root/scripts/validate_checkpoint.py" "$@"

