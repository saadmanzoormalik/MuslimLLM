import os
import signal
import time

from ...db import get_conn
from ..service import ensure_context_sync_ready
from .queue import enqueue_job


_running = True


def _stop(_signum, _frame) -> None:
    global _running
    _running = False


def _next_job() -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            select id from sync_jobs
            where status in ('authorized', 'failed_recoverable')
               or (status='running' and updated_at < now() - interval '10 minutes')
            order by created_at asc
            limit 1
            """
        ).fetchone()
    return str(row["id"]) if row else None


def run() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    ensure_context_sync_ready()
    poll_seconds = max(1.0, float(os.getenv("CONTEXT_SYNC_WORKER_POLL_SECONDS", "3")))
    while _running:
        job_id = _next_job()
        if not job_id:
            time.sleep(poll_seconds)
            continue
        try:
            enqueue_job(job_id)
        except Exception:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run()
