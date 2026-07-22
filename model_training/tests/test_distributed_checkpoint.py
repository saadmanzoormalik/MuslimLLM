import json
import pytest
import torch

from training.config import ModelConfig
from training.distributed.checkpointing import load_checkpoint, save_checkpoint
from training.model import MuslimLLM
from training.optim.hybrid import build_hybrid_optimizer


def test_corrupted_and_incompatible_checkpoints_are_rejected(tmp_path):
    config = ModelConfig(vocabulary_size=64, hidden_size=16, intermediate_size=32, num_layers=1, num_attention_heads=2, num_key_value_heads=1)
    model = MuslimLLM(config); optimizer = build_hybrid_optimizer(model, minimum_matrix_elements=16)
    path = tmp_path / "checkpoint.pt"; metadata = {"dataset_version": "v1", "world_size": 1}
    save_checkpoint(path, model, optimizer, step=0, metadata=metadata)
    with pytest.raises(ValueError, match="metadata mismatch"):
        load_checkpoint(path, model, optimizer, expected_metadata={"dataset_version": "v2"})
    with path.open("ab") as handle: handle.write(b"corruption")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_checkpoint(path, model, optimizer, expected_metadata=metadata)

