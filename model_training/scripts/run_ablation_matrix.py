from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.ablation import run_stage0_matrix

print(run_stage0_matrix(ROOT))

