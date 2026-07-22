from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from ..db import get_conn


def enforce(bucket: str, limit: int, window_seconds: int) -> None:
    now = datetime.now(UTC)
    with get_conn() as conn:
        row = conn.execute("select * from auth_rate_limits where bucket=%s for update", (bucket,)).fetchone()
        if not row:
            conn.execute("insert into auth_rate_limits (bucket,hits,window_started_at) values (%s,1,now())", (bucket,))
            return
        if row["blocked_until"] and row["blocked_until"] > now:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again shortly")
        if row["window_started_at"] < now - timedelta(seconds=window_seconds):
            conn.execute("update auth_rate_limits set hits=1,window_started_at=now(),blocked_until=null where bucket=%s", (bucket,))
            return
        hits = row["hits"] + 1
        blocked_until = now + timedelta(seconds=window_seconds) if hits > limit else None
        conn.execute("update auth_rate_limits set hits=%s,blocked_until=%s where bucket=%s", (hits, blocked_until, bucket))
        if hits > limit:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again shortly")
