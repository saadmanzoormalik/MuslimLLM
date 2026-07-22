import time
from collections import defaultdict

from fastapi import HTTPException, Request


WINDOW_SECONDS = 60
MAX_REQUESTS = 30
BUCKETS: dict[str, list[float]] = defaultdict(list)


def enforce_rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    BUCKETS[key] = [seen for seen in BUCKETS[key] if now - seen < WINDOW_SECONDS]
    if len(BUCKETS[key]) >= MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Too many authorization requests")
    BUCKETS[key].append(now)
