from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")


def test_sse_disables_buffering_and_emits_accepted_first():
    accepted = MAIN.index('yield emit("accepted"')
    plan = MAIN.index('yield emit("reasoning_plan"')
    token = MAIN.index('yield emit("token"')
    assert accepted < plan < token
    assert '"X-Accel-Buffering": "no"' in MAIN
    assert 'media_type="text/event-stream"' in MAIN
    assert "3200:3000" in COMPOSE and "8200:8000" in COMPOSE


def test_browser_uses_same_origin_stream_proxy():
    api = (ROOT / "frontend/lib/api.ts").read_text(encoding="utf-8")
    next_config = (ROOT / "frontend/next.config.ts").read_text(encoding="utf-8")
    assert '|| "/api"' in api
    assert 'source: "/api/:path*"' in next_config
    assert '"http://backend:8000"' in next_config
