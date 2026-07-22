import random


def backoff_seconds(attempt: int, base: float = 0.5, cap: float = 30.0) -> float:
    return min(cap, base * (2 ** attempt)) + random.uniform(0, 0.25)

