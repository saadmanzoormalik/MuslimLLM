from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Literal


RouteName = Literal["instant", "quick", "standard", "deep", "retrieval_required", "tool_required"]
UserMode = Literal["auto", "quick", "standard", "deep"]

EXACT_SOURCE = re.compile(r"\b(quote|verse|ayah|surah|hadith|reference|citation|source|according to)\b", re.I)
CURRENT = re.compile(r"\b(today|current|latest|this week|right now|recent|price|weather|news)\b", re.I)
ARITHMETIC = re.compile(r"^\s*(?:what is|calculate|compute)?\s*(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)\s*\??\s*$", re.I)
GREETING = re.compile(r"^\s*(?:hi|hello|hey|salam|assalamu alaikum|as-salamu alaykum)[!.\s]*$", re.I)


@dataclass(frozen=True)
class ChatRoute:
    name: RouteName
    reasoning_depth: Literal["quick", "standard", "deep"]
    retrieval_required: bool
    context_message_limit: int
    context_token_budget: int
    max_output_tokens: int
    reason: str


def route_request(message: str, *, requested_mode: UserMode, islamic: bool, fiqh: bool, values_sensitive: bool, imported_context: bool = False) -> ChatRoute:
    words = re.findall(r"\w+", message)
    exact_source = bool(EXACT_SOURCE.search(message))
    current = bool(CURRENT.search(message))
    arithmetic = bool(ARITHMETIC.match(message))
    greeting = bool(GREETING.match(message))
    complex_request = len(words) > 55 or message.count("?") > 1 or sum(term in message.lower() for term in ("compare", "analyze", "strategy", "trade-off", "step by step", "debug")) >= 2
    mandatory_retrieval = exact_source or current or fiqh or (islamic and len(words) > 10)

    if requested_mode == "deep": name, reason = "retrieval_required" if mandatory_retrieval else "deep", "user_selected_deep"
    elif requested_mode == "standard": name, reason = "retrieval_required" if mandatory_retrieval else "standard", "user_selected_standard"
    elif requested_mode == "quick": name, reason = "retrieval_required" if exact_source or fiqh else "quick", "user_selected_fast"
    elif arithmetic or greeting:
        name, reason = "instant", "deterministic_simple_request"
    elif mandatory_retrieval:
        name, reason = "retrieval_required", "source_sensitive_or_current"
    elif complex_request or imported_context:
        name, reason = "deep", "complex_or_large_context"
    elif len(words) <= 24 or values_sensitive:
        name, reason = "quick", "short_or_direct_request"
    else:
        name, reason = "standard", "balanced_default"

    depth = "deep" if name == "deep" else "standard" if name in {"standard", "retrieval_required", "tool_required"} else "quick"
    recent_cap = int(os.getenv("CHAT_RECENT_MESSAGE_LIMIT", "20"))
    context_cap = int(os.getenv("CHAT_CONTEXT_TOKEN_BUDGET", "6000"))
    limits = {
        "instant": (2, 500, 96),
        "quick": (6, 1400, int(os.getenv("LLM_QUICK_MAX_TOKENS", "500"))),
        "standard": (12, 3000, int(os.getenv("LLM_STANDARD_MAX_TOKENS", "1200"))),
        "deep": (20, 6000, int(os.getenv("LLM_DEEP_MAX_TOKENS", "3000"))),
        "retrieval_required": (12, 3500, int(os.getenv("LLM_STANDARD_MAX_TOKENS", "1200"))),
        "tool_required": (12, 3500, int(os.getenv("LLM_STANDARD_MAX_TOKENS", "1200"))),
    }
    recent, context, output = limits[name]
    recent = min(recent, recent_cap)
    context = min(context, context_cap)
    return ChatRoute(name, depth, name == "retrieval_required", recent, context, output, reason)


def deterministic_instant_answer(message: str) -> str | None:
    match = ARITHMETIC.match(message)
    if match:
        left, operator, right = float(match.group(1)), match.group(2), float(match.group(3))
        if operator == "+": result = left + right
        elif operator == "-": result = left - right
        elif operator == "*": result = left * right
        elif right == 0: return "Division by zero is undefined."
        else: result = left / right
        return str(int(result)) if result.is_integer() else str(round(result, 10))
    if GREETING.match(message):
        return "Wa alaykum as-salam. How can I help?" if "salam" in message.lower() else "Hello. How can I help?"
    return None
