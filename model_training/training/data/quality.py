import math
import re


def quality_components(text: str, *, source_authority: float = 0.5, language_confidence: float = 1.0, pii_risk: float = 0.0, toxicity: float = 0.0):
    words = re.findall(r"\w+", text.lower())
    diversity = len(set(words)) / max(1, len(words))
    repetition = 1 - diversity
    formatting = float(bool(text.strip()) and "\x00" not in text)
    citation_density = min(1.0, len(re.findall(r"\b(?:19|20)\d{2}\b|\b\d{1,3}:\d{1,3}\b", text)) / max(1, len(words) / 100))
    density = min(1.0, math.log1p(len(words)) / math.log(1000))
    components = {"language_confidence": language_confidence, "formatting_quality": formatting, "lexical_diversity": diversity, "repetition_risk": repetition, "semantic_density": density, "citation_density": citation_density, "source_authority": source_authority, "pii_risk": pii_risk, "toxicity": toxicity}
    score = 0.16 * language_confidence + 0.12 * formatting + 0.12 * diversity + 0.12 * density + 0.15 * source_authority + 0.1 * citation_density + 0.12 * (1 - repetition) + 0.06 * (1 - pii_risk) + 0.05 * (1 - toxicity)
    return components | {"weighted_quality_score": round(score, 6)}

