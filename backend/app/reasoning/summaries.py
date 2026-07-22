from __future__ import annotations

import os

from .schemas import ReasoningPlan

SUMMARY_ENABLED = os.getenv("REASONING_SUMMARY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def create_reasoning_summary(plan: ReasoningPlan, operations: dict) -> list[str]:
    if not SUMMARY_ENABLED:
        return []
    mode_summary = {
        "fiqh_sensitive": "Treated this as a context-sensitive jurisprudential question without presenting a binding fatwa.",
        "islamic_knowledge": "Separated source-backed Islamic material from interpretation and broader context.",
        "values_sensitive": "Checked the recommendation against honesty, justice, dignity, responsibility, and avoidance of harm.",
        "science": "Used a science-first explanation without adding religious framing where it was not needed.",
        "technical": "Focused on the technical requirement and checked the answer for practical consistency.",
        "research": "Separated established information from interpretation and compared the relevant factors.",
        "contextual": "Used relevant prior context while keeping imported material subordinate to current instructions.",
        "general": "Focused on the user’s direct question and a clear, practical answer.",
    }
    summary = [mode_summary[plan.mode]]
    if operations.get("context_reviewed"):
        summary.append("Reviewed relevant conversation or project context.")
    if operations.get("sources_retrieved"):
        summary.append(f"Reviewed {operations['sources_retrieved']} relevant source passages and retained citation traceability.")
    elif operations.get("retrieval_attempted"):
        summary.append("Checked the local source corpus; no reliable supporting passage was available.")
    if operations.get("uncertainty_checked"):
        summary.append("Considered uncertainty and material trade-offs before finalizing the response.")
    return summary[:4]
