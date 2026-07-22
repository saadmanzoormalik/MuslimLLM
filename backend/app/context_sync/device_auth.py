import hashlib
from datetime import UTC, datetime, timedelta

from ..db import get_conn


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def save_device_transaction(provider_id: str, local_connection_id: str, broker_connection_id: str, state: str, return_uri: str, ttl_seconds: int = 600) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            insert into device_auth_transactions
              (provider_id,local_connection_id,broker_connection_id,device_state_hash,return_uri,expires_at)
            values (%s,%s,%s,%s,%s,%s)
            """,
            (provider_id, local_connection_id, broker_connection_id, _digest(state), return_uri, datetime.now(UTC) + timedelta(seconds=ttl_seconds)),
        )


def claim_device_transaction(provider_id: str, state: str) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            """
            update device_auth_transactions set status='exchanging'
            where provider_id=%s and device_state_hash=%s and status='authorizing' and expires_at>now()
            returning *
            """,
            (provider_id, _digest(state)),
        ).fetchone()
    if not row:
        raise ValueError("Device authorization state expired or invalid")
    return row


def complete_device_transaction(transaction_id: str) -> None:
    with get_conn() as conn:
        conn.execute("update device_auth_transactions set status='used',used_at=now(),device_state_hash=gen_random_uuid()::text where id=%s", (transaction_id,))


def fail_device_transaction(transaction_id: str) -> None:
    with get_conn() as conn:
        conn.execute("update device_auth_transactions set status='failed' where id=%s", (transaction_id,))
