import json

from ..database import get_conn


def audit(event_type: str, outcome: str, provider_id: str | None = None, connection_id: str | None = None, grant_id: str | None = None, details: dict | None = None) -> None:
    safe_details = {key: value for key, value in (details or {}).items() if "token" not in key.lower() and "secret" not in key.lower()}
    with get_conn() as conn:
        conn.execute(
            """
            insert into auth_broker_audit_log (connection_id,grant_id,provider_id,event_type,outcome,details_json)
            values (%s,%s,%s,%s,%s,%s::jsonb)
            """,
            (connection_id, grant_id, provider_id, event_type, outcome, json.dumps(safe_details)),
        )
