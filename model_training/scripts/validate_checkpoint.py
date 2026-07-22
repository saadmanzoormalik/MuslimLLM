import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(); parser.add_argument("checkpoint"); args = parser.parse_args()
path = Path(args.checkpoint); signature = json.loads(path.with_suffix(path.suffix + ".sha256.json").read_text())
actual = hashlib.sha256(path.read_bytes()).hexdigest()
if actual != signature["sha256"]: raise SystemExit("Checkpoint hash mismatch")
print(json.dumps({"valid": True, "step": signature["step"], "sha256": actual}, indent=2))

