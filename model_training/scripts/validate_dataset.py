import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from training.data.manifests import immutable_manifest

parser = argparse.ArgumentParser(); parser.add_argument("manifest"); args = parser.parse_args()
result = immutable_manifest(args.manifest)
if not result["dataset_version"] or result["record_count"] < 1: raise SystemExit("Dataset manifest is not trainable")
print(json.dumps(result, indent=2))

