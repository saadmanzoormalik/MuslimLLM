import re


def script_signals(text: str):
    arabic = len(re.findall(r"[\u0600-\u06ff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = max(1, arabic + latin)
    return {"arabic_script": arabic / total, "latin_script": latin / total, "confidence": max(arabic, latin) / total}

