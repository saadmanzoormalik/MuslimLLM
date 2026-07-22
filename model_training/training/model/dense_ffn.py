import torch
from torch import nn
from torch.nn import functional as F


class SwiGLUFFN(nn.Module):
    def __init__(self, hidden_size: int, intermediate_size: int, dropout: float = 0.0):
        super().__init__()
        self.gate_up = nn.Linear(hidden_size, 2 * intermediate_size, bias=False)
        self.down = nn.Linear(intermediate_size, hidden_size, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gate, value = self.gate_up(x).chunk(2, dim=-1)
        return self.dropout(self.down(F.silu(gate) * value))

