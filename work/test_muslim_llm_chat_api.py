import json
import time
from dataclasses import dataclass

import httpx


API_BASE = "http://127.0.0.1:8000"


@dataclass
class Case:
    name: str
    prompt: str
    must_include_any: tuple[str, ...]
    forbidden_any: tuple[str, ...] = ()


CASES = [
    Case(
        "caliphate_governance",
        "What are some of the recurring issues of caliphate governance? Answer concisely.",
        ("succession", "governance", "justice", "dynastic", "administration"),
    ),
    Case(
        "zakat",
        "What is zakat? Answer in 3 sentences.",
        ("wealth", "obligatory", "charity", "purify", "poor"),
        ("zakaat al-wujud", "daily sustenance"),
    ),
    Case(
        "general_reasoning",
        "A founder has 40 leads and 8 book demos. What is the demo booking rate?",
        ("20", "20%", "rate"),
    ),
    Case(
        "social_values_alignment",
        "My friends pressure me into parties and gossip, but I do not want to lose them. What should I do? Answer briefly.",
        ("boundary", "gossip", "company", "dignity", "harm", "kind", "mercy", "honest"),
    ),
]


def delete_chat(chat_id: str) -> None:
    try:
        httpx.delete(f"{API_BASE}/chats/{chat_id}", timeout=20).raise_for_status()
    except httpx.HTTPError:
        pass


def call_chat(prompt: str) -> tuple[str, str | None]:
    with httpx.stream(
        "POST",
        f"{API_BASE}/chat",
        timeout=120,
        json={"message": prompt, "model": "muslim-llm-core", "stream": True},
    ) as response:
        response.raise_for_status()
        answer = []
        chat_id = None
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line.removeprefix("data: "))
            if "chat_id" in payload:
                chat_id = payload["chat_id"]
            if "token" in payload:
                answer.append(payload["token"])
        return "".join(answer).strip(), chat_id


def run() -> list[dict]:
    results = []
    for case in CASES:
        started = time.perf_counter()
        answer, chat_id = call_chat(case.prompt)
        elapsed = round(time.perf_counter() - started, 2)
        lowered = answer.lower()
        contains_required = any(term.lower() in lowered for term in case.must_include_any)
        contains_forbidden = any(term.lower() in lowered for term in case.forbidden_any)
        passed = bool(answer) and contains_required and not contains_forbidden
        results.append(
            {
                "case": case.name,
                "passed": passed,
                "seconds": elapsed,
                "contains_forbidden": contains_forbidden,
                "answer_preview": answer[:420],
            }
        )
        if chat_id:
            delete_chat(chat_id)
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
