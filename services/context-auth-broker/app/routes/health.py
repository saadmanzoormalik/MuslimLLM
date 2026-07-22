from fastapi import APIRouter

from ..config import settings
from ..database import get_conn
from ..providers.registry import public_providers


router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
def health():
    with get_conn() as conn:
        conn.execute("select 1").fetchone()
    return {"ok": True, "service": "context-auth-broker", "environment": settings.environment, "content_storage": "disabled"}


@router.get("/providers")
def providers():
    return public_providers()
