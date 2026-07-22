import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx


BACKEND = "http://127.0.0.1:8000"
BROKER = "http://127.0.0.1:8100"
PROVIDER = "http://127.0.0.1:8200"


def services_ready() -> bool:
    try:
        return all(
            httpx.get(url, timeout=2).status_code == 200
            for url in (f"{BACKEND}/health", f"{BROKER}/v1/health", f"{PROVIDER}/health")
        )
    except httpx.HTTPError:
        return False


def approve_url(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query["approve"] = "1"
    return urlunparse(parsed._replace(query=urlencode(query)))


def create_ready_grant() -> dict:
    started = httpx.post(
        f"{BACKEND}/context-sync/connect/demo",
        json={"return_uri": "http://127.0.0.1:3000/context-sync"},
        timeout=10,
    )
    started.raise_for_status()
    start_data = started.json()
    provider_response = httpx.get(approve_url(start_data["authorization_url"]), follow_redirects=False, timeout=10)
    assert provider_response.status_code == 303
    broker_response = httpx.get(provider_response.headers["location"], follow_redirects=False, timeout=15)
    assert broker_response.status_code == 303
    callback_url = broker_response.headers["location"]
    callback_query = dict(parse_qsl(urlparse(callback_url).query))
    return {
        **start_data,
        "grant_id": callback_query["grant_id"],
        "state": callback_query["state"],
        "device_callback_url": callback_url,
    }


def complete_demo_flow() -> dict:
    flow = create_ready_grant()
    callback = httpx.get(flow["device_callback_url"], follow_redirects=False, timeout=60)
    assert callback.status_code == 303
    returned = dict(parse_qsl(urlparse(callback.headers["location"]).query))
    flow["job_id"] = returned["job"]
    return flow


def wait_for_job(job_id: str, timeout_seconds: float = 45) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last = {}
    while time.monotonic() < deadline:
        response = httpx.get(f"{BACKEND}/context-sync/status/{job_id}", timeout=5)
        response.raise_for_status()
        last = response.json()
        if last["status"] in {"completed", "completed_with_exceptions", "cancelled", "failed_recoverable"}:
            return last
        time.sleep(0.25)
    raise AssertionError(f"Job did not finish: {last}")
