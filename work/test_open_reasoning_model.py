import json
import os
import time
from dataclasses import dataclass

import httpx


API_BASE = "http://127.0.0.1:11434/v1"
MODEL = os.getenv("TEST_LLM_MODEL", "deepseek-r1:1.5b")


@dataclass
class Case:
    name: str
    prompt: str
    must_include_any: tuple[str, ...]


CASES = [
    Case(
        "math_reasoning",
        "Answer briefly. A trader buys 3 items for $7 each and sells the bundle for $30. What is the profit?",
        ("9", "$9", "profit"),
    ),
    Case(
        "islamic_history",
        "In 5 bullet points, what were recurring governance issues in caliphate history?",
        ("succession", "governance", "dynastic", "justice", "administration"),
    ),
    Case(
        "fiqh_nuance",
        "Briefly explain why madhab differences can exist without implying Islam is arbitrary.",
        ("evidence", "method", "jurists", "madhab", "principles"),
    ),
    Case(
        "general_planning",
        "Give a concise 3-step plan for validating a new SaaS product idea.",
        ("customer", "problem", "prototype", "interview", "metric"),
    ),
]


def call_model(prompt: str) -> str:
    response = httpx.post(
        f"{API_BASE}/chat/completions",
        timeout=90,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Muslim LLM. Answer directly and practically. "
                        "For Islamic or civilizational questions, use a Muslim-civilizational lens. "
                        "Do not include generic caveats."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 220,
            "options": {"num_predict": 220},
            "stream": False,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def visible_answer(text: str) -> str:
    if "</think>" in text:
        return text.split("</think>", 1)[1].strip()
    return text.strip()


def run() -> list[dict]:
    results = []
    for case in CASES:
        started = time.perf_counter()
        raw = call_model(case.prompt)
        elapsed = round(time.perf_counter() - started, 2)
        answer = visible_answer(raw)
        lowered = answer.lower()
        passed = bool(answer) and any(term.lower() in lowered for term in case.must_include_any)
        results.append(
            {
                "case": case.name,
                "passed": passed,
                "seconds": elapsed,
                "has_thinking_trace": "<think>" in raw and "</think>" in raw,
                "answer_preview": answer[:360],
            }
        )
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
