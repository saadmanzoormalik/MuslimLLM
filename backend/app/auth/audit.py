from fastapi import Request

from ..db import get_conn
from .security import Principal, token_hash


def request_ip_hash(request: Request) -> str:
    value = request.client.host if request.client else "unknown"
    return token_hash(f"ip:{value}")


def audit(request: Request, event: str, success: bool, provider: str | None = None, error: str | None = None, principal: Principal | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """insert into auth_audit_log
               (user_id,guest_id,event_type,provider,success,error_code,device_id,ip_hash)
               values (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                principal.subject_id if principal and principal.kind == "user" else None,
                principal.subject_id if principal and principal.kind == "guest" else None,
                event, provider, success, error,
                request.cookies.get("mllm_device"), request_ip_hash(request),
            ),
        )
