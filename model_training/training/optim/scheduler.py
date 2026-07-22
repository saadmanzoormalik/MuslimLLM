import math


def warmup_cosine(step: int, warmup_steps: int, total_steps: int, minimum_ratio: float = 0.1) -> float:
    if step < warmup_steps:
        return (step + 1) / max(1, warmup_steps)
    progress = min(1.0, (step - warmup_steps) / max(1, total_steps - warmup_steps))
    return minimum_ratio + (1 - minimum_ratio) * 0.5 * (1 + math.cos(math.pi * progress))

