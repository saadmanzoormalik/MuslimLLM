from fastapi import FastAPI, Request

from .config import settings
from .models import ensure_schema
from .routes import callbacks_router, connections_router, grants_router, health_router


app = FastAPI(title="Muslim LLM Context Authorization Broker", docs_url=None if settings.environment == "production" else "/docs")
app.include_router(connections_router)
app.include_router(callbacks_router)
app.include_router(grants_router)
app.include_router(health_router)


@app.on_event("startup")
def startup():
    if settings.environment == "production" and settings.encryption_key == "development-broker-key-change-me":
        raise RuntimeError("AUTH_BROKER_ENCRYPTION_KEY must be configured in production")
    ensure_schema()


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
