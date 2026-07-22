from __future__ import annotations

import torch
from torch.optim import Optimizer


def newton_schulz_orthogonalize(matrix: torch.Tensor, steps: int = 5, eps: float = 1e-7) -> torch.Tensor:
    """Approximate the polar factor in float32 using a stable quintic iteration."""
    x = matrix.float()
    transposed = x.shape[0] > x.shape[1]
    if transposed:
        x = x.T
    x = x / x.norm().clamp_min(eps)
    a, b, c = 3.4445, -4.7750, 2.0315
    for _ in range(steps):
        gram = x @ x.T
        x = a * x + (b * gram + c * (gram @ gram)) @ x
    return x.T if transposed else x


class Muon(Optimizer):
    def __init__(self, params, lr=0.02, momentum=0.95, nesterov=True, ns_steps=5, weight_decay=0.0, eps=1e-7):
        super().__init__(params, dict(lr=lr, momentum=momentum, nesterov=nesterov, ns_steps=ns_steps, weight_decay=weight_decay, eps=eps))

    @torch.no_grad()
    def step(self, closure=None):
        loss = closure() if closure is not None else None
        for group in self.param_groups:
            for parameter in group["params"]:
                if parameter.grad is None:
                    continue
                if parameter.ndim != 2:
                    raise ValueError("Muon accepts only matrix-valued parameters")
                grad = parameter.grad.float()
                state = self.state[parameter]
                momentum = state.setdefault("momentum_buffer", torch.zeros_like(parameter, dtype=torch.float32))
                momentum.mul_(group["momentum"]).add_(grad)
                update = grad.add(momentum, alpha=group["momentum"]) if group["nesterov"] else momentum
                update = newton_schulz_orthogonalize(update, group["ns_steps"], group["eps"])
                scale = max(1.0, (parameter.shape[0] / parameter.shape[1]) ** 0.5)
                if group["weight_decay"]:
                    parameter.mul_(1 - group["lr"] * group["weight_decay"])
                parameter.add_(update.to(parameter.dtype), alpha=-group["lr"] * scale)
                state["update_norm"] = float(update.norm().item())
                state["orthogonalization_residual"] = float(((update @ update.T) - torch.eye(update.shape[0], device=update.device)).norm().item()) if update.shape[0] <= update.shape[1] else 0.0
        return loss

