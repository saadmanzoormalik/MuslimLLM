import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from evaluation.release_gate import evaluate_release

parser = argparse.ArgumentParser(); parser.add_argument("report"); args = parser.parse_args()
result = evaluate_release(json.loads(Path(args.report).read_text()))
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["passed"] else 2)

