import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


FIRST_TOKEN_TIMEOUT_SECONDS = float(os.getenv("CHAT_FIRST_TOKEN_TIMEOUT_SECONDS", "45"))
TOTAL_TIMEOUT_SECONDS = float(os.getenv("CHAT_TOTAL_TIMEOUT_SECONDS", "180"))
STREAM_HEARTBEAT_SECONDS = float(os.getenv("CHAT_STREAM_HEARTBEAT_SECONDS", "5"))
MAX_RETRIES = int(os.getenv("CHAT_MAX_RETRIES", "1"))
ENABLE_FALLBACK_RESPONSE = os.getenv("CHAT_ENABLE_FALLBACK_RESPONSE", "true").lower() in {"1", "true", "yes", "on"}
ENABLE_REASONING_STATUS = os.getenv("CHAT_ENABLE_REASONING_STATUS", "true").lower() in {"1", "true", "yes", "on"}
ENABLE_REASONING_SUMMARY = os.getenv("CHAT_ENABLE_REASONING_SUMMARY", "true").lower() in {"1", "true", "yes", "on"}
MAX_USER_MESSAGE_CHARS = int(os.getenv("CHAT_MAX_USER_MESSAGE_CHARS", "24000"))

ISLAMIC_TERMS = {
    "islam", "muslim", "quran", "hadith", "sunnah", "fiqh", "fatwa", "madhab",
    "zakat", "salah", "ramadan", "hajj", "umrah", "halal", "haram", "sharia",
    "prophet", "sahaba", "caliph", "caliphate", "khilafah", "ummah", "masjid",
}
FIQH_TERMS = {
    "fiqh", "fatwa", "madhab", "ruling", "halal", "haram", "zakat", "salah",
    "pray", "prayer", "qasar", "qasr", "fasting", "ramadan", "hajj", "umrah", "wudu", "nikah", "divorce",
    "inheritance", "mahr", "interest", "riba",
}
SCIENCE_TECH_TERMS = {
    "code", "python", "javascript", "api", "bug", "science", "math", "physics",
    "biology", "chemistry", "engineering", "algorithm", "database", "server",
}
TOPIC_LABELS = [
    ("zakat", "zakat, wealth, and obligation"),
    ("salah", "prayer, discipline, and worship"),
    ("prayer", "prayer, discipline, and worship"),
    ("ramadan", "fasting, restraint, and taqwa"),
    ("fasting", "fasting, restraint, and taqwa"),
    ("marriage", "marriage, mercy, and rights"),
    ("wife", "family, mercy, and rights"),
    ("husband", "family, mercy, and rights"),
    ("divorce", "family law, dignity, and harm reduction"),
    ("friend", "friendship, character, and boundaries"),
    ("conflict", "conflict, justice, and mercy"),
    ("business", "business, amanah, and lawful value"),
    ("trade", "trade routes, trust, and civilization"),
    ("caliph", "governance, legitimacy, and accountability"),
    ("caliphate", "governance, legitimacy, and accountability"),
    ("abbasid", "institutions, scholarship, and power"),
    ("ottoman", "institutions, law, and empire"),
    ("python", "code correctness and clarity"),
    ("javascript", "code correctness and clarity"),
    ("api", "systems, reliability, and edge cases"),
]


@dataclass
class ChatRun:
    chat_id: str | None = None
    message_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid4()))
    answer_mode: str = "general"
    query_is_islamic: bool = False
    values_sensitive: bool = False
    madhab_sensitive: bool = False
    fatwa_sensitive: bool = False
    needs_scholar_consultation: bool = False
    used_rag: bool = False
    source_confidence: str = "not_used"
    reliability_status: str = "idle"
    started_at: float = field(default_factory=time.monotonic)
    warnings: list[str] = field(default_factory=list)

    def metadata(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "answer_mode": self.answer_mode,
            "used_rag": self.used_rag,
            "source_confidence": self.source_confidence,
            "madhab_sensitive": self.madhab_sensitive,
            "fatwa_sensitive": self.fatwa_sensitive,
            "needs_scholar_consultation": self.needs_scholar_consultation,
            "reliability_status": self.reliability_status,
        }


def classify_chat_run(message: str, query_is_islamic: bool, values_sensitive: bool) -> ChatRun:
    lower = message.lower()
    has_fiqh = any(term in lower for term in FIQH_TERMS)
    has_islamic = query_is_islamic or has_fiqh or any(term in lower for term in ISLAMIC_TERMS)
    has_science = any(term in lower for term in SCIENCE_TECH_TERMS)
    run = ChatRun(
        query_is_islamic=has_islamic,
        values_sensitive=values_sensitive,
        madhab_sensitive=has_fiqh,
        fatwa_sensitive=has_fiqh or "personal ruling" in lower,
        needs_scholar_consultation=has_fiqh and any(word in lower for word in ["my", "me", "i ", "family", "wife", "husband"]),
    )
    if has_fiqh:
        run.answer_mode = "fiqh_sensitive"
    elif has_islamic:
        run.answer_mode = "islamic_civilizational"
    elif has_science:
        run.answer_mode = "technical_or_science"
    elif values_sensitive:
        run.answer_mode = "values_sensitive"
    return run


def validate_message(message: str) -> str | None:
    if not message or not message.strip():
        return "Please enter a question."
    if len(message) > MAX_USER_MESSAGE_CHARS:
        return f"Please shorten the message to under {MAX_USER_MESSAGE_CHARS} characters."
    return None


def infer_topic_label(message: str) -> str:
    lower = message.lower()
    for needle, label in TOPIC_LABELS:
        if needle in lower:
            return label
    words = re.findall(r"[A-Za-z][A-Za-z'-]{2,}", message)
    filtered = [word for word in words if word.lower() not in {"what", "how", "why", "does", "with", "from", "that", "this", "about", "some", "give", "tell", "explain"}]
    if not filtered:
        return "your question"
    return " ".join(filtered[:4]).lower()


def status_steps(run: ChatRun, message: str = "") -> list[tuple[str, str]]:
    topic = infer_topic_label(message)
    steps = [
        ("validating", f"Reading your intent around {topic}"),
        ("preparing_context", f"Pulling together the right context for {topic}"),
        ("reasoning", "Checking the answer against Muslim values"),
    ]
    if run.answer_mode == "fiqh_sensitive":
        steps.extend([
            ("reasoning", f"Treating {topic} with source sensitivity"),
            ("reasoning", "Anchoring the response in Quran and Sunnah values"),
            ("reasoning", "Checking whether madhab differences may matter"),
        ])
    elif run.answer_mode == "technical_or_science":
        steps.extend([
            ("reasoning", f"Checking the factual and technical shape of {topic}"),
            ("reasoning", "Keeping the answer useful without over-framing it religiously"),
        ])
    elif run.values_sensitive:
        steps.extend([
            ("reasoning", f"Reading the human stakes inside {topic}"),
            ("reasoning", "Balancing mercy, honesty, dignity, and accountability"),
        ])
    elif run.query_is_islamic:
        steps.extend([
            ("reasoning", f"Looking for grounded Islamic context on {topic}"),
            ("reasoning", "Separating principle, history, and modern opinion"),
        ])
    else:
        steps.append(("reasoning", f"Finding the clearest practical path for {topic}"))
    steps.extend([
        ("calling_model", "Shaping the response before writing"),
        ("streaming", "Writing the answer in a clear Muslim LLM voice"),
    ])
    return steps


def fallback_response(run: ChatRun) -> str:
    base = (
        "I’m having trouble generating a full response from the local model right now. "
        "Your message was saved. Please retry, or check that the local model is running."
    )
    if run.fatwa_sensitive or run.query_is_islamic or run.values_sensitive:
        base += (
            " Since this may involve religious guidance, please retry when the local model is "
            "available and consult a qualified scholar for personal rulings."
        )
    return base


def reasoning_summary(run: ChatRun, source_note: str = "") -> str:
    if not ENABLE_REASONING_SUMMARY:
        return ""
    parts = ["Checked the request type", "applied Muslim-values alignment"]
    if run.used_rag:
        parts.append("looked for source-backed evidence")
    if run.madhab_sensitive:
        parts.append("marked it as madhab-sensitive")
    if source_note:
        parts.append("noted limited corpus support")
    return "; ".join(parts) + "."


def sse(event: str, payload: dict[str, Any]) -> str:
    safe_payload = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {safe_payload}\n\n"


def split_tokens(text: str):
    for token in re.split(r"(\s+)", text):
        if token:
            yield token
