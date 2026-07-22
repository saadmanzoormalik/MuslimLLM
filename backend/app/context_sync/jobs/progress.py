from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


def estimate_remaining_seconds(
    processed_items: int,
    total_items: int,
    elapsed_seconds: float,
    recent_throughput: float,
    remaining_file_bytes: int,
    average_file_bytes_per_second: float,
) -> int | None:
    """Estimate remaining real work, returning None until a useful rate exists."""
    if total_items <= 0:
        return 0
    remaining_items = max(total_items - max(processed_items, 0), 0)
    if remaining_items == 0 and remaining_file_bytes <= 0:
        return 0
    if processed_items <= 0 or elapsed_seconds <= 0 or recent_throughput <= 0:
        return None

    item_seconds = remaining_items / recent_throughput
    if remaining_file_bytes > 0:
        if average_file_bytes_per_second <= 0:
            return None
        file_seconds = remaining_file_bytes / average_file_bytes_per_second
        item_seconds = max(item_seconds, file_seconds)
    return max(1, int(round(item_seconds)))


@dataclass(frozen=True)
class _Sample:
    timestamp: float
    processed: int
    bytes_processed: int


class ThroughputEstimator:
    """Rolling item/byte ETA based on observed worker commits."""

    def __init__(self, total: int, total_file_bytes: int = 0, window_seconds: float = 30.0):
        self.total = max(total, 0)
        self.total_file_bytes = max(total_file_bytes, 0)
        self.started = time.monotonic()
        self.window_seconds = max(window_seconds, 1.0)
        self.samples: deque[_Sample] = deque([_Sample(self.started, 0, 0)])

    def observe(self, processed: int, bytes_processed: int = 0) -> None:
        now = time.monotonic()
        self.samples.append(_Sample(now, max(processed, 0), max(bytes_processed, 0)))
        while len(self.samples) > 2 and now - self.samples[0].timestamp > self.window_seconds:
            self.samples.popleft()

    def remaining(self, processed: int, bytes_processed: int = 0) -> int | None:
        self.observe(processed, bytes_processed)
        latest = self.samples[-1]
        baseline = self.samples[0]
        rolling_elapsed = max(latest.timestamp - baseline.timestamp, 0.0)
        rolling_items = max(latest.processed - baseline.processed, 0)
        rolling_bytes = max(latest.bytes_processed - baseline.bytes_processed, 0)
        recent_throughput = rolling_items / rolling_elapsed if rolling_elapsed > 0 else 0.0
        byte_throughput = rolling_bytes / rolling_elapsed if rolling_elapsed > 0 else 0.0
        return estimate_remaining_seconds(
            processed_items=processed,
            total_items=self.total,
            elapsed_seconds=max(latest.timestamp - self.started, 0.0),
            recent_throughput=recent_throughput,
            remaining_file_bytes=max(self.total_file_bytes - bytes_processed, 0),
            average_file_bytes_per_second=byte_throughput,
        )

    def percent(self, processed: int) -> float:
        if self.total <= 0:
            return 100.0
        return round(min(100, (processed / self.total) * 100), 2)
