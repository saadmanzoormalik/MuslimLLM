import math


def expert_capacity(token_count: int, top_k: int, expert_count: int, factor: float) -> int:
    if token_count < 1 or top_k < 1 or expert_count < 1 or factor <= 0:
        raise ValueError("Capacity inputs must be positive")
    return max(1, math.ceil(factor * token_count * top_k / expert_count))

