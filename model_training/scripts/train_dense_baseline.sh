#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "$root/scripts/train_tiny.sh" --config "$root/configs/model/unit_dense.yaml" --output "$root/experiments/dense-baseline" --optimizer adamw "$@"

