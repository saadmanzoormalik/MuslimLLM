from __future__ import annotations

import json
import hashlib
import platform
from pathlib import Path
import random
import subprocess
import time
import uuid

import torch

from .config import ModelConfig
from .distributed.checkpointing import save_checkpoint
from .model import MuslimLLM
from .optim.diagnostics import optimizer_diagnostics
from .optim.hybrid import build_hybrid_optimizer


def synthetic_batch(config, batch_size, sequence_length, generator):
    # Learnable modular sequence gives Stage 0 a meaningful convergence signal.
    starts = torch.randint(0, config.vocabulary_size, (batch_size, 1), generator=generator)
    offsets = torch.arange(sequence_length)[None, :]
    return (starts + offsets) % config.vocabulary_size


def train_experiment(config_path, output_dir, *, steps=8, optimizer_type="hybrid", seed=17, batch_size=2, sequence_length=32):
    torch.manual_seed(seed); random.seed(seed)
    config = ModelConfig.from_yaml(config_path)
    model = MuslimLLM(config)
    if optimizer_type == "adamw":
        base = torch.optim.AdamW(model.parameters(), lr=3e-4)
        class Wrapper:
            partition = type("Partition", (), {"muon_names": [], "adamw_names": [name for name, _ in model.named_parameters()]})()
            muon, adamw = None, base
            def zero_grad(self, set_to_none=True): self.adamw.zero_grad(set_to_none=set_to_none)
            def step(self): self.adamw.step()
            def state_dict(self): return {"muon": None, "adamw": self.adamw.state_dict(), "muon_names": [], "adamw_names": self.partition.adamw_names}
            def load_state_dict(self, state): self.adamw.load_state_dict(state["adamw"])
        optimizer = Wrapper()
    else:
        optimizer = build_hybrid_optimizer(model, minimum_matrix_elements=1024)
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    generator = torch.Generator().manual_seed(seed)
    metrics, started = [], time.perf_counter()
    for step in range(1, steps + 1):
        input_ids = synthetic_batch(config, batch_size, sequence_length, generator)
        result = model(input_ids, input_ids)
        if not torch.isfinite(result["loss"]): raise FloatingPointError("Non-finite training loss")
        optimizer.zero_grad(); result["loss"].backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        row = {"step": step, "loss": float(result["loss"].item()), "auxiliary_loss": float(result["auxiliary_loss"].item()), "gradient_norm": float(grad_norm), "routing": result["routing_metrics"]}
        metrics.append(row)
    elapsed = time.perf_counter() - started
    config_bytes = Path(config_path).read_bytes()
    try:
        code_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[2], stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        code_commit = "unversioned-workspace"
    metadata = {"run_id": run_id, "code_commit": code_commit, "config": str(config_path), "config_sha256": hashlib.sha256(config_bytes).hexdigest(), "dataset_version": "synthetic-stage0-v1", "curriculum_version": "random-baseline-v1", "tokenizer_version": "byte-v1", "optimizer": optimizer_type, "seed": seed, "hardware": platform.platform(), "torch_version": torch.__version__, "precision": "float32", "world_size": 1, "estimated_cost_usd": 0.0}
    signature = save_checkpoint(output / "checkpoint.pt", model, optimizer, step=steps, metadata=metadata, data_cursor=steps * batch_size * sequence_length)
    report = {"metadata": metadata, "parameter_counts": model.parameter_counts(), "steps": steps, "tokens": steps * batch_size * sequence_length, "elapsed_seconds": elapsed, "tokens_per_second": steps * batch_size * sequence_length / elapsed, "initial_loss": metrics[0]["loss"], "final_loss": metrics[-1]["loss"], "metrics": metrics, "optimizer_diagnostics": optimizer_diagnostics(optimizer), "checkpoint": signature}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
