from __future__ import annotations

import random


def bounded_backoff(attempt: int, *, maximum_seconds: float = 300.0) -> float:
    return min(maximum_seconds, (2 ** min(max(attempt, 0), 8)) + random.uniform(0, 1))


def should_continue_waiting(attempt: int, *, maximum_attempts: int = 2016) -> bool:
    return 0 <= attempt < maximum_attempts
