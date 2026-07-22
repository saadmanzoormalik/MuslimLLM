import asyncio
import json
import os

import httpx


API_BASE = os.getenv("MUSLIM_LLM_API", "http://127.0.0.1:8000")


def parse_sse(raw: str) -> list[tuple[str, dict]]:
    events = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event = "message"
        data = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            if line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        events.append((event, data))
    return events


async def test_chat_stream_reliability_contract():
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{API_BASE}/chat",
            json={"message": "What are some issues of the caliphate?", "model": "muslim-llm-core", "stream": True},
        )
        response.raise_for_status()
        events = parse_sse(response.text)
    names = [event for event, _ in events]
    tokens = [data.get("content") or data.get("token") for event, data in events if event == "token"]
    assert "metadata" in names
    assert "status" in names
    assert "complete" in names
    assert "".join(token for token in tokens if token).strip()


async def test_chat_diagnostics_contract():
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{API_BASE}/chat/diagnostics")
        response.raise_for_status()
        payload = response.json()
    for key in ["backend", "database", "local_model_api", "model_response_test", "streaming", "recommendations"]:
        assert key in payload


if __name__ == "__main__":
    asyncio.run(test_chat_stream_reliability_contract())
    asyncio.run(test_chat_diagnostics_contract())
    print("reliability checks passed")
