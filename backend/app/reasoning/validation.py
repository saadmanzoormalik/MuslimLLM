from __future__ import annotations

import re

FORBIDDEN_VISIBLE_TERMS = ("chain of thought", "developer instruction", "private scratchpad", "system prompt", "token budget")


def safe_task_label(label: str) -> str:
    cleaned = " ".join(label.split())[:100]
    if any(term in cleaned.lower() for term in FORBIDDEN_VISIBLE_TERMS):
        return "Checking the response"
    return cleaned


def validate_answer(answer: str, citations: list) -> dict:
    cited_numbers = {int(value) for value in re.findall(r"\[(\d+)\]", answer)}
    invalid_citations = sorted(number for number in cited_numbers if number < 1 or number > len(citations))
    return {
        "has_answer": bool(answer.strip()),
        "citation_count": len(citations),
        "citations_consistent": not invalid_citations,
        "invalid_citation_numbers": invalid_citations,
    }
