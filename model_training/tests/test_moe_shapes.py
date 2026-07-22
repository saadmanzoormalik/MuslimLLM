import torch

from training.config import ModelConfig
from training.model import MuslimLLM


def config(shared=0):
    return ModelConfig(vocabulary_size=256, hidden_size=32, intermediate_size=64, num_layers=2, num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=32, moe_enabled=True, moe_layer_frequency=1, num_routed_experts=4, num_shared_experts=shared, experts_per_token=2, expert_intermediate_size=48, expert_capacity_factor=2.0)


def test_moe_preserves_shape_and_backpropagates():
    model = MuslimLLM(config())
    tokens = torch.randint(0, 256, (2, 12))
    result = model(tokens, tokens)
    assert result["logits"].shape == (2, 12, 256)
    result["loss"].backward()
    assert all(parameter.grad is not None for name, parameter in model.named_parameters() if "experts" in name)


def test_shared_expert_is_always_active():
    model = MuslimLLM(config(shared=1))
    model(torch.randint(0, 256, (1, 8)))["logits"].sum().backward()
    shared = [parameter for name, parameter in model.named_parameters() if ".shared.experts." in name]
    assert shared and all(parameter.grad is not None for parameter in shared)

