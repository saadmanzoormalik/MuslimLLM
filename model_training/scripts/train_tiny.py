import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.trainer import train_experiment

parser = argparse.ArgumentParser()
parser.add_argument("--config", default=str(ROOT / "configs/model/unit_dense.yaml"))
parser.add_argument("--output", default=str(ROOT / "experiments/tiny"))
parser.add_argument("--steps", type=int, default=8)
parser.add_argument("--optimizer", choices=["adamw", "hybrid"], default="hybrid")
args = parser.parse_args()
report = train_experiment(args.config, args.output, steps=args.steps, optimizer_type=args.optimizer)
print({key: report[key] for key in ("initial_loss", "final_loss", "tokens_per_second", "parameter_counts")})

