from __future__ import annotations

import re
from typing import Any

from .schemas import QueryPolicy


def required_reviewers(policy: QueryPolicy) -> list[str]:
    reviewers: list[str] = []
    categories = set(policy.categories)
    if categories & {"Qur'an", "Hadith", "Islamic knowledge", "fiqh", "family law", "Islamic finance"}:
        reviewers.append("islamic_source_verifier")
    if policy.fiqh_sensitive:
        reviewers.append("fiqh_and_madhab_reviewer")
    if policy.scientific_sources_required:
        reviewers.append("scientific_accuracy_reviewer")
    if policy.historical_sources_required or policy.current_sources_required:
        reviewers.append("historical_and_geopolitical_reviewer")
    if policy.values_sensitive:
        reviewers.append("islamic_values_alignment_reviewer")
    return reviewers


def deterministic_review_flags(answer: str, policy: QueryPolicy) -> dict[str, Any]:
    text = answer.lower()
    flags: list[str] = []
    if policy.scientific_sources_required and re.search(r"\b(quran|hadith) proves? (?:the )?(?:scientific|empirical)\b", text):
        flags.append("religious_text_substituted_for_empirical_evidence")
    if policy.fiqh_sensitive and "binding fatwa" in text:
        flags.append("fatwa_impersonation")
    if policy.madhab_sensitive and not any(term in text for term in ("madhab", "hanafi", "maliki", "shafi", "hanbali", "school")):
        flags.append("madhab_difference_not_addressed")
    if policy.current_sources_required and not re.search(r"\b20\d{2}\b", text):
        flags.append("current_answer_missing_date_context")
    return {"passed": not flags, "flags": flags, "reviewers": required_reviewers(policy)}
