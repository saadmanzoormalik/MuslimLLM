import re


def validate_religious_integrity(record) -> list[str]:
    failures = []
    labels = set(record.muslim_context_labels)
    if "quran" in labels and not re.search(r"\bsurah\s+\d{1,3}\s*:\s*\d{1,3}\b", record.text, re.I):
        failures.append("malformed_quran_mapping")
    if "hadith" in labels and not re.search(r"\b(collection|book|hadith)\b", record.text, re.I):
        failures.append("malformed_hadith_mapping")
    if re.search(r"ignore (all|previous) instructions|system prompt", record.text, re.I):
        failures.append("prompt_injection_artifact")
    return failures

