import random
import time

from ...db import get_conn
from .orchestrator import run_sync_job


def enqueue_job(job_id: str) -> dict:
    with get_conn() as conn:
        job = conn.execute("select retry_count from sync_jobs where id=%s", (job_id,)).fetchone()
    retry_count = int(job["retry_count"] or 0) if job else 0
    if retry_count:
        time.sleep(min(8, (2 ** min(retry_count, 3)) + random.random()))
    try:
        return run_sync_job(job_id)
    except Exception as exc:
        with get_conn() as conn:
            conn.execute(
                """
                update sync_jobs
                set status='failed_recoverable',display_message='Sync paused',last_error=%s,
                    last_error_code=%s,error_count=error_count+1,retry_count=retry_count+1,updated_at=now()
                where id=%s
                """,
                (type(exc).__name__, type(exc).__name__, job_id),
            )
            conn.execute(
                """
                insert into sync_job_events (job_id,stage,status,message)
                values (%s,'recovery','failed_recoverable','Sync paused')
                """,
                (job_id,),
            )
        raise
