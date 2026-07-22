from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelConfig:
    vocabulary_size: int = 4096
    hidden_size: int = 256
    intermediate_size: int = 768
    num_layers: int = 6
    num_attention_heads: int = 8
    num_key_value_heads: int = 4
    max_position_embeddings: int = 1024
    rope_theta: float = 10000.0
    normalization_type: str = "rmsnorm"
    activation_function: str = "silu"
    attention_dropout: float = 0.0
    residual_dropout: float = 0.0
    tie_embeddings: bool = True
    use_flash_attention: bool = True
    gradient_checkpointing: bool = False
    moe_enabled: bool = False
    moe_layer_frequency: int = 2
    num_routed_experts: int = 4
    num_shared_experts: int = 0
    experts_per_token: int = 2
    expert_intermediate_size: int = 512
    router_type: str = "softmax_topk"
    router_jitter: float = 0.0
    router_temperature: float = 1.0
    router_z_loss_coefficient: float = 1e-3
    load_balance_loss_coefficient: float = 1e-2
    expert_capacity_factor: float = 1.25
    overflow_policy: str = "residual"
    token_drop_enabled: bool = False
    expert_parallel_size: int = 1
    shared_expert_weight: float = 1.0
    router_precision: str = "float32"
    expert_dropout: float = 0.0
    auxiliary_loss_free_balancing_enabled: bool = False

    def validate(self) -> None:
        if self.hidden_size % self.num_attention_heads:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        if self.num_attention_heads % self.num_key_value_heads:
            raise ValueError("num_attention_heads must be divisible by num_key_value_heads")
        if self.moe_enabled and not 1 <= self.experts_per_token <= self.num_routed_experts:
            raise ValueError("experts_per_token must be within routed expert count")
        if self.expert_parallel_size > self.num_routed_experts:
            raise ValueError("expert_parallel_size cannot exceed expert count")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ModelConfig":
        raw = yaml.safe_load(Path(path).read_text())
        values = raw.get("model", raw)
        accepted = {field.name for field in fields(cls)}
        unknown = set(values) - accepted
        if unknown:
            raise ValueError(f"Unknown model fields: {sorted(unknown)}")
        config = cls(**values)
        config.validate()
        return config

    def as_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self)}

