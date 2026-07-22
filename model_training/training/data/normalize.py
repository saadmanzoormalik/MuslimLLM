import unicodedata


def conservative_normalize(text: str) -> str:
    # NFC composes equivalent code points without stripping Arabic diacritics.
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))

