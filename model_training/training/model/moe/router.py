from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class Routing:
    probabilities: torch.Tensor
    weights: torch.Tensor
    indices: torch.Tensor
    logits: torch.Tensor


class TopKRouter(nn.Module):
    def __init__(self, hidden_size: int, experts: int, top_k: int, temperature: float = 1.0, jitter: float = 0.0):
        super().__init__()
        self.projection = nn.Linear(hidden_size, experts, bias=False)
        self.top_k, self.temperature, self.jitter = top_k, temperature, jitter

    def forward(self, tokens: torch.Tensor, deterministic: bool = False) -> Routing:
        router_input = tokens.float()
        if self.training and self.jitter and not deterministic:
            router_input = router_input * torch.empty_like(router_input).uniform_(1 - self.jitter, 1 + self.jitter)
        logits = self.projection(router_input) / self.temperature
        probabilities = F.softmax(logits, dim=-1)
        weights, indices = probabilities.topk(self.top_k, dim=-1)
        weights = weights / weights.sum(dim=-1, keepdim=True).clamp_min(1e-9)
        return Routing(probabilities, weights.to(tokens.dtype), indices, logits)

