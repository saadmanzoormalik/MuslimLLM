import json

from psycopg import Connection


def save_checkpoint(conn: Connection, job_id: str, stage: str, processed: int, payload: dict, cursor: str | None = None) -> None:
    encoded = json.dumps(payload, default=str)
    conn.execute(
        """
        insert into sync_checkpoints (job_id, stage, processed, checkpoint_json, cursor)
        values (%s,%s,%s,%s::jsonb,%s)
        """,
        (job_id, stage, processed, encoded, cursor),
    )
    conn.execute(
        """
        update sync_jobs
        set checkpoint_json=%s::jsonb,provider_cursor=coalesce(%s,provider_cursor),
            last_processed_object=coalesce(%s,last_processed_object),updated_at=now()
        where id=%s
        """,
        (encoded, cursor, cursor, job_id),
    )
    conn.commit()
