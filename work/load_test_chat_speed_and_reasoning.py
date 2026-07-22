import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx


QUICK = ["What is 2 + 2?", "Hello", "What is photosynthesis?", "Write a one-line Python greeting."]
MIXED = ["Can I lie to close an important sale?", "Write a Python function for binary search.", "Explain why the sky appears blue."]
RAG = ["How should a traveler pray?", "Quote a Quran reference about justice."]
DEEP = ["Compare the governance trade-offs across the Rashidun, Umayyad, and Abbasid periods, distinguishing evidence from interpretation."]


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, max(0, int(len(ordered) * q) - 1))], 2)


async def authenticate(client, base):
    response = await client.post(f"{base}/auth/guest", json={"claim_existing_workspace": False})
    response.raise_for_status()


async def run_one(client, base, prompt, mode="auto"):
    started = time.perf_counter()
    accepted_ms = first_token_ms = None
    names, content, route = [], [], None
    try:
        async with client.stream("POST", f"{base}/chat", json={"message": prompt, "stream": True, "reasoning_depth": mode}) as response:
            response.raise_for_status()
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                frames = buffer.split("\n\n")
                buffer = frames.pop()
                for frame in frames:
                    name = next((line[7:] for line in frame.splitlines() if line.startswith("event: ")), "")
                    raw = next((line[6:] for line in frame.splitlines() if line.startswith("data: ")), "{}")
                    data = json.loads(raw)
                    names.append(name)
                    if name == "accepted" and accepted_ms is None:
                        accepted_ms = (time.perf_counter() - started) * 1000
                        route = data.get("route")
                    if name == "token":
                        if first_token_ms is None:
                            first_token_ms = (time.perf_counter() - started) * 1000
                        content.append(data.get("content") or data.get("token") or "")
        answer = "".join(content).strip()
        return {"ok": bool(answer), "accepted_ms": accepted_ms, "first_token_ms": first_token_ms, "total_ms": (time.perf_counter() - started) * 1000, "route": route, "thinking": "reasoning_plan" in names, "complete": "complete" in names, "empty": not bool(answer), "interrupted": "complete" not in names}
    except Exception as exc:
        return {"ok": False, "accepted_ms": accepted_ms, "first_token_ms": first_token_ms, "total_ms": (time.perf_counter() - started) * 1000, "route": route, "thinking": "reasoning_plan" in names, "complete": False, "empty": True, "interrupted": True, "error": type(exc).__name__}


async def main(args):
    timeout = httpx.Timeout(240, connect=10)
    async with httpx.AsyncClient(timeout=timeout) as client:
        await authenticate(client, args.base)
        jobs = [(QUICK[index % len(QUICK)], "auto") for index in range(args.quick)]
        sequential = [await run_one(client, args.base, prompt, mode) for prompt, mode in jobs]
        concurrent_jobs = [(MIXED[index % len(MIXED)], "auto") for index in range(args.mixed)]
        concurrent = await asyncio.gather(*(run_one(client, args.base, prompt, mode) for prompt, mode in concurrent_jobs))
        rag = [await run_one(client, args.base, RAG[index % len(RAG)], "standard") for index in range(args.rag)]
        deep = [await run_one(client, args.base, DEEP[index % len(DEEP)], "deep") for index in range(args.deep)]
        results = sequential + concurrent + rag + deep
        diagnostics = (await client.get(f"{args.base}/diagnostics/chat-performance")).json()
    first = [row["first_token_ms"] for row in results if row.get("first_token_ms") is not None]
    total = [row["total_ms"] for row in results]
    report = {
        "request_count": len(results),
        "success_rate": round(100 * sum(row["ok"] for row in results) / len(results), 2),
        "thinking_rate": round(100 * sum(row["thinking"] for row in results) / len(results), 2),
        "silent_failures": sum(not row["ok"] and not row.get("error") for row in results),
        "empty_responses": sum(row["empty"] for row in results),
        "stream_interruptions": sum(row["interrupted"] for row in results),
        "accepted_ms": {"p50": percentile([row["accepted_ms"] for row in results if row.get("accepted_ms") is not None], .5), "p95": percentile([row["accepted_ms"] for row in results if row.get("accepted_ms") is not None], .95)},
        "first_token_ms": {"p50": percentile(first, .5), "p95": percentile(first, .95)},
        "total_ms": {"p50": percentile(total, .5), "p95": percentile(total, .95)},
        "backend_diagnostics": diagnostics,
        "results": results,
    }
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    if report["success_rate"] < 100 or report["thinking_rate"] < 100 or report["empty_responses"] or report["silent_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8200")
    parser.add_argument("--quick", type=int, default=50)
    parser.add_argument("--mixed", type=int, default=20)
    parser.add_argument("--rag", type=int, default=20)
    parser.add_argument("--deep", type=int, default=10)
    parser.add_argument("--output", default="work/chat-speed-reasoning-results.json")
    asyncio.run(main(parser.parse_args()))
