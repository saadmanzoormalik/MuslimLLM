import torch
from torch import nn

from ..dense_ffn import SwiGLUFFN


class SharedExperts(nn.Module):
    def __init__(self, count: int, hidden: int, intermediate: int, dropout: float, weight: float):
        super().__init__()
        self.experts = nn.ModuleList([SwiGLUFFN(hidden, intermediate, dropout) for _ in range(count)])
        self.weight = weight

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if not self.experts:
            return torch.zeros_like(x)
        return self.weight * sum((expert(x) for expert in self.experts), torch.zeros_like(x)) / len(self.experts)

