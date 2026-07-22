import math

import torch


def routing_metrics(probabilities: torch.Tensor, indices: torch.Tensor, experts: int, dropped: int, overflow: int) -> dict[str, float]:
    counts = torch.bincount(indices.flatten(), minlength=experts).float()
    normalized = counts / counts.sum().clamp_min(1)
    entropy = -(normalized * normalized.clamp_min(1e-9).log()).sum()
    return {
        "expert_utilization_variance": counts.var(unbiased=False).item(),
        "expert_entropy": (entropy / math.log(experts)).item() if experts > 1 else 1.0,
        "router_confidence": probabilities.max(dim=-1).values.mean().item(),
        "dropped_token_rate": dropped / max(1, indices.shape[0]),
        "overflow_rate": overflow / max(1, indices.shape[0]),
        "dead_expert_count": float((counts == 0).sum().item()),
        "dominant_expert_share": normalized.max().item(),
        "tokens_per_expert": counts.tolist(),
    }

