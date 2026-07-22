from __future__ import annotations

import os


def email_detection_enabled() -> bool:
    """Email inspection is off unless a separately authorized connector is enabled."""
    return os.getenv("CONTEXT_SYNC_OPENAI_EMAIL_DETECTION_ENABLED", "false").lower() == "true"


def approved_sender(sender: str) -> bool:
    address = sender.strip().lower()
    return address.endswith("@openai.com") or address == "noreply@tm.openai.com"
