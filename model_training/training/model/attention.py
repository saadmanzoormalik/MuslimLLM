import torch
from torch import nn
from torch.nn import functional as F


def apply_rope(x: torch.Tensor, positions: torch.Tensor, theta: float) -> torch.Tensor:
    dim = x.shape[-1]
    inv = 1.0 / (theta ** (torch.arange(0, dim, 2, device=x.device, dtype=torch.float32) / dim))
    angles = positions.float()[:, None] * inv[None, :]
    cos, sin = angles.cos()[None, None], angles.sin()[None, None]
    even, odd = x[..., 0::2], x[..., 1::2]
    return torch.stack((even * cos - odd * sin, even * sin + odd * cos), dim=-1).flatten(-2)


class CausalSelfAttention(nn.Module):
    def __init__(self, hidden: int, heads: int, kv_heads: int, dropout: float, rope_theta: float):
        super().__init__()
        self.heads, self.kv_heads, self.head_dim = heads, kv_heads, hidden // heads
        self.q = nn.Linear(hidden, heads * self.head_dim, bias=False)
        self.k = nn.Linear(hidden, kv_heads * self.head_dim, bias=False)
        self.v = nn.Linear(hidden, kv_heads * self.head_dim, bias=False)
        self.out = nn.Linear(hidden, hidden, bias=False)
        self.dropout, self.rope_theta = dropout, rope_theta

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, _ = x.shape
        shape_q = (batch, length, self.heads, self.head_dim)
        shape_kv = (batch, length, self.kv_heads, self.head_dim)
        q = self.q(x).view(shape_q).transpose(1, 2)
        k = self.k(x).view(shape_kv).transpose(1, 2)
        v = self.v(x).view(shape_kv).transpose(1, 2)
        positions = torch.arange(length, device=x.device)
        q, k = apply_rope(q, positions, self.rope_theta), apply_rope(k, positions, self.rope_theta)
        repeat = self.heads // self.kv_heads
        k, v = k.repeat_interleave(repeat, dim=1), v.repeat_interleave(repeat, dim=1)
        output = F.scaled_dot_product_attention(q, k, v, dropout_p=self.dropout if self.training else 0.0, is_causal=True)
        return self.out(output.transpose(1, 2).contiguous().view(batch, length, -1))

