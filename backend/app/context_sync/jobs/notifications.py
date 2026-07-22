import json

from psycopg import Connection


def notify_in_app(conn: Connection, job_id: str, provider_id: str, message: str) -> None:
    conn.execute(
        """
        insert into sync_audit_log (job_id, provider_id, event_type, details_json)
        values (%s,%s,'in_app_notification',%s::jsonb)
        """,
        (job_id, provider_id, json.dumps({"message": message})),
    )
