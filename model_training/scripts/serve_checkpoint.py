import argparse
from pathlib import Path
import sys

import torch
import uvicorn

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from serving import api
from serving.engine import InferenceEngine
from training.config import ModelConfig
from training.data.tokenizer import ReversibleByteTokenizer
from training.model import MuslimLLM

parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); parser.add_argument("--checkpoint", required=True); parser.add_argument("--port", type=int, default=8300); args = parser.parse_args()
model = MuslimLLM(ModelConfig.from_yaml(args.config)); model.load_state_dict(torch.load(args.checkpoint, map_location="cpu")["model"])
api.engine = InferenceEngine(model, ReversibleByteTokenizer())
uvicorn.run(api.app, host="127.0.0.1", port=args.port)

