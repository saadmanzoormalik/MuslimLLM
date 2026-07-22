from __future__ import annotations

import re
from uuid import uuid4

from .schemas import FabricInput, QueryPolicy, ValidatedInput


MAX_QUERY_CHARS = 24000

PROMPT_INJECTION_PATTERNS = (
    r"\bignore (?:all |any )?(?:previous|prior|system|developer) instructions?\b",
    r"\boverride (?:the )?(?:system|developer|safety|policy)\b",
    r"\bact as (?:the )?(?:system|developer|administrator)\b",
    r"\b(?:reveal|show|print|repeat|leak) (?:the |your )?(?:system prompt|developer instructions?|hidden prompt|secrets?)\b",
    r"\bprompt injection\b",
)

CATEGORY_TERMS: dict[str, set[str]] = {
    "scientific": {"science", "scientific", "physics", "chemistry", "biology", "photosynthesis", "climate", "astronomy", "experiment"},
    "technical": {"code", "python", "javascript", "typescript", "algorithm", "api", "database", "docker", "software", "engineering", "binary search"},
    "medical": {"medical", "medicine", "doctor", "disease", "diagnosis", "treatment", "symptom", "medication", "health"},
    "legal": {"legal", "lawyer", "lawsuit", "court", "contract", "criminal", "regulation"},
    "financial": {"financial", "finance", "investment", "loan", "mortgage", "tax", "profit", "sale", "business"},
    "personal": {"my life", "my wife", "my husband", "my family", "relationship", "personal", "advice"},
    "professional": {"workplace", "career", "manager", "employee", "employer", "client", "customer", "sale", "business"},
    "social": {"friend", "community", "society", "social", "neighbor", "gossip", "disagreement"},
    "ethical": {"ethic", "moral", "honest", "dishonest", "lie", "lying", "deceive", "fair", "justice", "harm"},
    "Qur'an": {"qur'an", "quran", "ayah", "surah", "verse"},
    "Hadith": {"hadith", "sunnah", "bukhari", "muslim collection", "isnad"},
    "Islamic knowledge": {"islam", "islamic", "muslim", "sharia", "sunnah", "tafsir", "sirah"},
    "fiqh": {"fiqh", "fatwa", "madhab", "hanafi", "maliki", "shafi", "hanbali", "jafari", "zahiri", "halal", "haram", "rak'ah", "rak‘ah", "rakah", "wudu", "salah"},
    "family law": {"nikah", "marriage", "divorce", "talaq", "khul", "custody", "inheritance", "mahr"},
    "Islamic finance": {"riba", "zakat", "sukuk", "murabaha", "takaful", "islamic finance"},
    "history": {"history", "historical", "empire", "ottoman", "abbasid", "umayyad", "mamluk", "mughal", "safavid", "andalus"},
    "Muslim civilization": {"civilization", "caliphate", "khilafah", "muslim world", "trade route", "waqf"},
    "geopolitics": {"geopolitic", "government", "foreign policy", "war", "sanction", "state", "border"},
    "military history": {"battle", "military history", "army", "campaign", "siege"},
    "current affairs": {"today", "this week", "current", "currently", "latest", "recent", "right now", "news"},
}

VALUES_CATEGORIES = {"personal", "professional", "social", "ethical", "family law", "financial", "Islamic finance"}
HIGH_RISK_CATEGORIES = {"medical", "legal", "family law", "fiqh", "Islamic finance"}


def _contains_term(text: str, term: str) -> bool:
    if " " in term or "'" in term or "‘" in term:
        return term in text
    return bool(re.search(rf"\b{re.escape(term)}\b", text))


def validate_fabric_input(payload: FabricInput) -> ValidatedInput:
    original = payload.query
    clean = re.sub(r"\s+", " ", original).strip()
    flags = [
        "prompt_injection" for pattern in PROMPT_INJECTION_PATTERNS
        if re.search(pattern, clean, flags=re.IGNORECASE)
    ]
    flags = sorted(set(flags))
    if not clean:
        return ValidatedInput(
            query_id=str(uuid4()), original_query=original, clean_query="", security_flags=flags,
            valid=False, rejection_reason="empty_query",
        )
    if len(clean) > MAX_QUERY_CHARS:
        return ValidatedInput(
            query_id=str(uuid4()), original_query=original, clean_query=clean[:MAX_QUERY_CHARS], security_flags=flags,
            valid=False, rejection_reason="query_too_long",
        )
    return ValidatedInput(
        query_id=str(uuid4()), original_query=original, clean_query=clean,
        security_flags=flags, valid=True,
    )


def classify_query_policy(query: str, *, current_information_allowed: bool = True) -> QueryPolicy:
    text = re.sub(r"\s+", " ", query.lower()).strip()
    categories = [
        category for category, terms in CATEGORY_TERMS.items()
        if any(_contains_term(text, term) for term in terms)
    ]
    if not categories:
        categories = ["general"]

    category_set = set(categories)
    fiqh_sensitive = bool(category_set & {"fiqh", "family law", "Islamic finance"})
    madhab_sensitive = fiqh_sensitive and any(
        term in text for term in ("madhab", "hanafi", "maliki", "shafi", "hanbali", "jafari", "zahiri", "rak'ah", "rak‘ah", "rakah", "traveler", "traveller")
    )
    values_sensitive = bool(category_set & VALUES_CATEGORIES)
    scientific_required = bool(category_set & {"scientific", "medical", "technical"})
    historical_required = bool(category_set & {"history", "Muslim civilization", "geopolitics", "military history"})
    current_required = current_information_allowed and "current affairs" in category_set
    quran_required = "Qur'an" in category_set and any(term in text for term in ("quote", "verse", "ayah", "surah", "says"))
    hadith_required = "Hadith" in category_set
    islamic_topic = bool(category_set & {"Qur'an", "Hadith", "Islamic knowledge", "fiqh", "family law", "Islamic finance"})

    if fiqh_sensitive:
        answer_mode = "fiqh"
    elif current_required and "geopolitics" in category_set:
        answer_mode = "current_geopolitics"
    elif historical_required:
        answer_mode = "history_and_civilization"
    elif scientific_required:
        answer_mode = "scientific_or_technical"
    elif islamic_topic:
        answer_mode = "islamic_knowledge"
    elif values_sensitive:
        answer_mode = "values_sensitive"
    else:
        answer_mode = "general"

    citation_required = quran_required or hadith_required or fiqh_sensitive or historical_required or current_required or "medical" in category_set
    minimum_source_count = 0
    minimum_source_tier = 0
    diversity = False
    if quran_required or hadith_required:
        minimum_source_count, minimum_source_tier = 1, 4
    if fiqh_sensitive:
        minimum_source_count, minimum_source_tier, diversity = 2, 3, True
    if historical_required:
        minimum_source_count, minimum_source_tier = 2, 3
        diversity = "geopolitics" in category_set
    if scientific_required:
        minimum_source_count, minimum_source_tier = (2, 3) if "medical" in category_set else (1, 2)
    if current_required:
        minimum_source_count, minimum_source_tier, diversity = 3, 3, True

    if category_set & {"medical", "legal", "family law"}:
        risk_level = "high"
    elif category_set & HIGH_RISK_CATEGORIES or current_required:
        risk_level = "medium"
    else:
        risk_level = "low"

    return QueryPolicy(
        categories=categories,
        answer_mode=answer_mode,
        values_sensitive=values_sensitive,
        quran_required=quran_required,
        hadith_required=hadith_required,
        fiqh_sensitive=fiqh_sensitive,
        madhab_sensitive=madhab_sensitive,
        scientific_sources_required=scientific_required,
        historical_sources_required=historical_required,
        current_sources_required=current_required,
        minimum_source_tier=minimum_source_tier,
        minimum_source_count=minimum_source_count,
        source_diversity_required=diversity,
        citation_required=citation_required,
        scholar_consultation_may_be_needed=fiqh_sensitive or bool(category_set & {"medical", "legal", "family law"}),
        risk_level=risk_level,
    )
