import re


def adversarial_risk_flags(text: str):
    patterns = {"sectarian_incitement": r"\b(?:kill|attack|expel)\b.{0,30}\b(?:sect|community|believers)\b", "deception": r"\bhow to (?:defraud|deceive|scam)\b"}
    return [name for name, pattern in patterns.items() if re.search(pattern, text, re.I)]

