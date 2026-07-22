from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

from ..config import ModelConfig
from .attention import CausalSelfAttention
from .dense_ffn import SwiGLUFFN
from .moe.layer import MoELayer


class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x):
        return self.weight * x * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + self.eps).to(x.dtype)


class DecoderBlock(nn.Module):
    def __init__(self, config: ModelConfig, index: int):
        super().__init__()
        self.attention_norm = RMSNorm(config.hidden_size)
        self.attention = CausalSelfAttention(config.hidden_size, config.num_attention_heads, config.num_key_value_heads, config.attention_dropout, config.rope_theta)
        self.ffn_norm = RMSNorm(config.hidden_size)
        use_moe = config.moe_enabled and (index + 1) % config.moe_layer_frequency == 0
        self.ffn = MoELayer(config) if use_moe else SwiGLUFFN(config.hidden_size, config.intermediate_size, config.residual_dropout)
        self.dropout = nn.Dropout(config.residual_dropout)

    def forward(self, x):
        x = x + self.dropout(self.attention(self.attention_norm(x)))
        if isinstance(self.ffn, MoELayer):
            ffn, auxiliary = self.ffn(self.ffn_norm(x))
        else:
            ffn, auxiliary = self.ffn(self.ffn_norm(x)), x.new_zeros(())
        return x + self.dropout(ffn), auxiliary


class MuslimLLM(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        config.validate()
        self.config = config
        self.embedding = nn.Embedding(config.vocabulary_size, config.hidden_size)
        self.layers = nn.ModuleList([DecoderBlock(config, index) for index in range(config.num_layers)])
        self.final_norm = RMSNorm(config.hidden_size)
        self.lm_head = nn.Linear(config.hidden_size, config.vocabulary_size, bias=False)
        if config.tie_embeddings:
            self.lm_head.weight = self.embedding.weight
        self.apply(self._init)

    @staticmethod
    def _init(module):
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, std=0.02)

    def forward(self, input_ids, labels=None):
        if input_ids.shape[1] > self.config.max_position_embeddings:
            raise ValueError("Sequence exceeds max_position_embeddings")
        x, auxiliary = self.embedding(input_ids), input_ids.new_zeros((), dtype=torch.float32)
        for layer in self.layers:
            x, layer_aux = layer(x)
            auxiliary = auxiliary + layer_aux.float()
        logits = self.lm_head(self.final_norm(x))
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), labels[:, 1:].reshape(-1)) + auxiliary
        return {"logits": logits, "loss": loss, "auxiliary_loss": auxiliary, "routing_metrics": self.routing_metrics()}

    def routing_metrics(self):
        return [layer.ffn.last_metrics for layer in self.layers if isinstance(layer.ffn, MoELayer)]

    def parameter_counts(self):
        total = sum(parameter.numel() for parameter in self.parameters())
        if not self.config.moe_enabled:
            return {"total": total, "activated_estimate": total}
        expert_total = sum(parameter.numel() for layer in self.layers if isinstance(layer.ffn, MoELayer) for expert in layer.ffn.experts for parameter in expert.parameters())
        activated_experts = expert_total * self.config.experts_per_token / self.config.num_routed_experts
        return {"total": total, "activated_estimate": int(total - expert_total + activated_experts)}
