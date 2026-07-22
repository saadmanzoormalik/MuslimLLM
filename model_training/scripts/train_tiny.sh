#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
"$root/.venv/bin/python" "$root/scripts/train_tiny.py" "$@"

