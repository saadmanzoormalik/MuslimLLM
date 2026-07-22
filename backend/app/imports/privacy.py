import re


PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|system) instructions",
    r"you are now",
    r"developer message",
    r"system prompt",
    r"exfiltrate",
    r"send .*api key",
    r"reveal .*secret",
]

TOKEN_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{12,}",
    r"api[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9_.-]{12,}",
    r"bearer\s+[A-Za-z0-9_.-]{12,}",
]


def scan_import_for_prompt_injection(text: str) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in PROMPT_INJECTION_PATTERNS if re.search(pattern, lowered, re.I)]


def strip_provider_system_prompts_if_needed(role: str, content: str) -> tuple[str, str]:
    if role == "system":
        return "unknown", "[Provider system message stripped and stored as user-context metadata.]"
    return role, content


def classify_imported_content_as_user_context(content: str) -> dict:
    return {"classification": "user_context", "trusted_as_instruction": False, "content_length": len(content)}


def prevent_imported_context_instruction_override(text: str) -> str:
    return text.replace("system prompt", "provider prompt").replace("ignore previous instructions", "quoted unsafe instruction")


def redact_tokens_from_logs(text: str) -> str:
    redacted = text
    for pattern in TOKEN_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED_TOKEN]", redacted, flags=re.I)
    return redacted


def revoke_provider_credentials(provider: str) -> dict:
    return {"provider": provider, "revoked": True, "stored_credentials": False}
