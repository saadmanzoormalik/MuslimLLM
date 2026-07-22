from training.config import ModelConfig
from training.model import MuslimLLM
from training.optim.hybrid import build_hybrid_optimizer


def test_hybrid_partition_is_disjoint_and_router_uses_adamw():
    model = MuslimLLM(ModelConfig(vocabulary_size=128, hidden_size=32, intermediate_size=64, num_layers=2, num_attention_heads=4, num_key_value_heads=2, moe_enabled=True, moe_layer_frequency=1, expert_intermediate_size=48))
    optimizer = build_hybrid_optimizer(model, minimum_matrix_elements=64)
    names = optimizer.partition
    assert set(names.muon_names).isdisjoint(names.adamw_names)
    assert any("router" in name for name in names.adamw_names)
    assert all("embedding" not in name and "norm" not in name for name in names.muon_names)

