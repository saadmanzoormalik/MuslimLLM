import asyncio
import json
import os
import time
from pathlib import Path

import httpx


API_BASE = os.getenv("MUSLIM_LLM_API", "http://127.0.0.1:8000")
OUTPUT = Path("work/reliability-results.json")
PROMPTS = [
    "What are some issues of the caliphate?",
    "How should I handle a friendship conflict in a way aligned with Islamic values?",
    "Explain zakat in simple terms.",
    "Write a tiny FastAPI health endpoint.",
    "Summarize the importance of Muslim trade routes.",
]


def parse_events(raw: str):
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event = "message"
        data = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        yield event, data


async def run_one(client: httpx.AsyncClient, prompt: str, index: int):
    started = time.perf_counter()
    result = {"index": index, "prompt": prompt, "ok": False, "tokens": 0, "status_events": [], "latency_ms": None, "error": None}
    try:
        response = await client.post(f"{API_BASE}/chat", json={"message": prompt, "model": "muslim-llm-core", "stream": True})
        response.raise_for_status()
        content = []
        for event, data in parse_events(response.text):
            if event == "status":
                result["status_events"].append(data.get("label"))
            elif event == "token":
                token = data.get("content") or data.get("token") or ""
                content.append(token)
                result["tokens"] += 1
            elif event == "complete":
                result["reliability_status"] = data.get("reliability_status")
        result["ok"] = bool("".join(content).strip())
    except Exception as exc:
        result["error"] = type(exc).__name__
    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    return result


async def main():
    concurrency = int(os.getenv("CHAT_LOAD_CONCURRENCY", "2"))
    async with httpx.AsyncClient(timeout=180) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def guarded(prompt: str, index: int):
            async with semaphore:
                return await run_one(client, prompt, index)

        results = await asyncio.gather(*(guarded(prompt, index) for index, prompt in enumerate(PROMPTS, start=1)))
    passed = sum(1 for item in results if item["ok"])
    report = {
        "api_base": API_BASE,
        "total": len(results),
        "passed": passed,
        "success_rate": round((passed / len(results)) * 100, 2),
        "results": results,
    }
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
