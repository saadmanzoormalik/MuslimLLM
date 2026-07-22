import asyncio
import json
import os

import httpx

API_BASE = os.getenv("MUSLIM_LLM_API", "http://127.0.0.1:8000")


def parse_sse(raw: str):
    parsed = []
    for block in raw.split("\n\n"):
        name = next((line[7:] for line in block.splitlines() if line.startswith("event: ")), None)
        payload = next((json.loads(line[6:]) for line in block.splitlines() if line.startswith("data: ")), {})
        if name:
            parsed.append((name, payload))
    return parsed


async def ask(client: httpx.AsyncClient, message: str):
    response = await client.post(f"{API_BASE}/chat", json={"message": message, "stream": True, "reasoning_depth": "standard"})
    response.raise_for_status()
    return parse_sse(response.text)


async def run():
    async with httpx.AsyncClient(timeout=150) as client:
        islamic = await ask(client, "What principles shaped zakat in Muslim society? Answer briefly.")
        neutral = await ask(client, "Explain photosynthesis briefly.")
        for events in (islamic, neutral):
            names = [name for name, _ in events]
            assert names[0] == "accepted"
            assert "reasoning_task_started" in names
            assert "reasoning_task_completed" in names
            assert "reasoning_summary" in names
            assert "token" in names and "complete" in names
            assert names.index("reasoning_plan") < names.index("token")
            assert "".join(payload.get("token", "") for name, payload in events if name == "token").strip()
        islamic_plan = next(payload for name, payload in islamic if name == "reasoning_plan")
        neutral_plan = next(payload for name, payload in neutral if name == "reasoning_plan")
        assert "sources" in {task["id"] for task in islamic_plan["tasks"]}
        assert "sources" not in {task["id"] for task in neutral_plan["tasks"]}
        chat_ids = {payload.get("chat_id") for events in (islamic, neutral) for _, payload in events if payload.get("chat_id")}
        for chat_id in chat_ids:
            await client.delete(f"{API_BASE}/chats/{chat_id}")


if __name__ == "__main__":
    asyncio.run(run())
    print("reasoning SSE contract checks passed")
