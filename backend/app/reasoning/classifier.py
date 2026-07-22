from __future__ import annotations

import re
from typing import Any

SCIENCE_TERMS = {
    "biology", "chemistry", "climate", "experiment", "evolution", "medicine", "physics",
    "photosynthesis", "scientific", "science",
}
TECHNICAL_TERMS = {"api", "bug", "code", "database", "docker", "fastapi", "javascript", "python", "server", "software", "sql", "typescript"}
RESEARCH_TERMS = {"analyze", "compare", "evidence", "history", "research", "sources", "study", "verify"}
CALCULATION_PATTERN = re.compile(r"(?:\d[\d,.]*\s*(?:%|percent|rate|total|times|divided|\+|-|\*|/))|(?:calculate|compute|equation)", re.I)


def classify_reasoning_request(
    user_message: str,
    conversation_context: list,
    base_classification: dict[str, Any],
) -> dict[str, Any]:
    lower = user_message.lower()
    words = re.findall(r"[a-z0-9']+", lower)
    has_science = any(term in lower for term in SCIENCE_TERMS)
    has_technical = any(term in lower for term in TECHNICAL_TERMS)
    has_research = any(term in lower for term in RESEARCH_TERMS)
    has_calculation = bool(CALCULATION_PATTERN.search(user_message))
    has_context = len(conversation_context) > 1 or bool(base_classification.get("project_context")) or bool(base_classification.get("imported_context"))
    fiqh = bool(base_classification.get("madhab_sensitive") or base_classification.get("fatwa_sensitive"))
    islamic = bool(base_classification.get("query_is_islamic"))
    values = bool(base_classification.get("values_sensitive"))
    complexity = "complex" if len(words) > 45 or user_message.count("?") > 1 or sum(token in lower for token in ("compare", "trade-off", "step by step", "analyze", "multiple", "plan")) >= 2 else "simple"

    if fiqh:
        mode = "fiqh_sensitive"
    elif islamic:
        mode = "islamic_knowledge"
    elif values:
        mode = "values_sensitive"
    elif has_science:
        mode = "science"
    elif has_technical:
        mode = "technical"
    elif has_context:
        mode = "contextual"
    elif has_research:
        mode = "research"
    else:
        mode = "general"
    return {
        "mode": mode,
        "complexity": complexity,
        "retrieval_required": islamic,
        "context_required": has_context,
        "values_sensitive": values,
        "islamic_knowledge": islamic,
        "fiqh_sensitive": fiqh,
        "science": has_science,
        "technical": has_technical,
        "calculation": has_calculation,
        "project_context": bool(base_classification.get("project_context")),
        "imported_context": bool(base_classification.get("imported_context")),
        "personal_context_matters": fiqh and bool(re.search(r"\b(i|my|me|we|our|wife|husband|family)\b", lower)),
    }
