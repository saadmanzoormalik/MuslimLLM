import math

import torch


def dispatch_and_combine(tokens, routing, experts, capacity_factor: float, drop: bool):
    token_count, hidden = tokens.shape
    capacity = max(1, math.ceil(capacity_factor * token_count * routing.indices.shape[1] / len(experts)))
    output = torch.zeros_like(tokens)
    accepted = torch.zeros(token_count, device=tokens.device, dtype=torch.bool)
    overflow = dropped = 0
    for expert_id, expert in enumerate(experts):
        positions = (routing.indices == expert_id).nonzero(as_tuple=False)
        if positions.shape[0] > capacity:
            overflow += positions.shape[0] - capacity
            positions = positions[:capacity]
        if not positions.numel():
            continue
        token_ids, slots = positions[:, 0], positions[:, 1]
        values = expert(tokens[token_ids]) * routing.weights[token_ids, slots, None]
        output.index_add_(0, token_ids, values)
        accepted[token_ids] = True
    if drop:
        dropped = int((~accepted).sum().item())
    else:
        output = output + tokens * (~accepted)[:, None]
    return output, dropped, overflow

