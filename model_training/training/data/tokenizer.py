from __future__ import annotations

import unicodedata


class ReversibleByteTokenizer:
    vocab_size = 256

    def encode(self, text: str):
        return list(text.encode("utf-8"))

    def decode(self, tokens):
        return bytes(tokens).decode("utf-8", errors="replace")


def tokenizer_metrics(tokenizer, samples: dict[str, list[str]]):
    results = {}
    for language, texts in samples.items():
        characters = sum(len(text) for text in texts)
        tokens = sum(len(tokenizer.encode(text)) for text in texts)
        reversible = all(tokenizer.decode(tokenizer.encode(text)) == text for text in texts)
        results[language] = {"fertility": tokens / max(1, characters), "reversible": reversible, "diacritics_preserved": all(unicodedata.normalize("NFC", tokenizer.decode(tokenizer.encode(text))) == unicodedata.normalize("NFC", text) for text in texts)}
    return results
