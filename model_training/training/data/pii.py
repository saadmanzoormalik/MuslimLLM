import re


def pii_findings(text: str):
    findings = []
    if re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", text): findings.append("email")
    if re.search(r"\b(?:\d[ -]*?){13,19}\b", text): findings.append("possible_payment_card")
    return findings

