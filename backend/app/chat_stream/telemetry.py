from __future__ import annotations

from collections import Counter, deque
import math


RECENT = deque(maxlen=500)


def record_performance(metrics: dict): RECENT.append(dict(metrics))


def percentile(values, quantile):
    if not values: return None
    ordered = sorted(values); index = min(len(ordered) - 1, max(0, math.ceil(quantile * len(ordered)) - 1)); return round(ordered[index], 2)


def performance_snapshot():
    rows = list(RECENT)
    first = [row["time_to_first_token_ms"] for row in rows if row.get("time_to_first_token_ms") is not None]
    total = [row["total_response_ms"] for row in rows if row.get("total_response_ms") is not None]
    stages = ("database_prewrite_ms", "classification_ms", "retrieval_ms", "queue_wait_ms", "model_generation_ms", "database_finalize_ms")
    averages = {stage: round(sum(row.get(stage, 0) for row in rows) / max(1, len(rows)), 2) for stage in stages}
    return {"sample_size": len(rows), "first_token_ms": {"p50": percentile(first, .5), "p95": percentile(first, .95)}, "total_ms": {"p50": percentile(total, .5), "p95": percentile(total, .95)}, "route_distribution": dict(Counter(row.get("route", "unknown") for row in rows)), "slowest_average_stage": max(averages, key=averages.get) if rows else None, "stage_average_ms": averages, "recent_failures": [row.get("failure") for row in rows if row.get("failure")][-10:]}

