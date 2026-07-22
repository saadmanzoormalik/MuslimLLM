#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "$root/scripts/train_tiny.sh" --config "$root/configs/model/unit_moe_shared.yaml" --output "$root/experiments/moe-muon" --optimizer hybrid "$@"

