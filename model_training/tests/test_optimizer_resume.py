import torch

from training.config import ModelConfig
from training.distributed.checkpointing import load_checkpoint, save_checkpoint
from training.model import MuslimLLM
from training.optim.hybrid import build_hybrid_optimizer


def test_hybrid_checkpoint_resumes(tmp_path):
    config = ModelConfig(vocabulary_size=64, hidden_size=16, intermediate_size=32, num_layers=1, num_attention_heads=2, num_key_value_heads=1)
    model = MuslimLLM(config); optimizer = build_hybrid_optimizer(model, minimum_matrix_elements=16)
    tokens = torch.randint(0, 64, (1, 8)); loss = model(tokens, tokens)["loss"]; loss.backward(); optimizer.step()
    metadata = {"dataset_version": "v1", "tokenizer_version": "byte-v1"}
    path = tmp_path / "checkpoint.pt"; save_checkpoint(path, model, optimizer, step=1, metadata=metadata)
    restored = MuslimLLM(config); restored_optimizer = build_hybrid_optimizer(restored, minimum_matrix_elements=16)
    payload = load_checkpoint(path, restored, restored_optimizer, expected_metadata=metadata)
    assert payload["step"] == 1
    assert all(torch.equal(a, b) for a, b in zip(model.parameters(), restored.parameters()))

