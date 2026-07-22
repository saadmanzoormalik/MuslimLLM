from collections import Counter
import random


def sample_mixture(records, weights: dict[str, float], count: int, seed: int, synthetic_cap: float = 0.2):
    rng = random.Random(seed)
    by_domain = {domain: [record for record in records if record.domain == domain] for domain in weights}
    domains = list(weights)
    selected, synthetic = [], 0
    while len(selected) < count:
        domain = rng.choices(domains, weights=[weights[item] for item in domains], k=1)[0]
        if not by_domain[domain]: continue
        candidate = rng.choice(by_domain[domain])
        if candidate.origin == "synthetic" and (synthetic + 1) / (len(selected) + 1) > synthetic_cap: continue
        selected.append(candidate); synthetic += candidate.origin == "synthetic"
    return selected


def mixture_metrics(records):
    return {"domains": dict(Counter(record.domain for record in records)), "languages": dict(Counter(record.language for record in records)), "synthetic_ratio": sum(record.origin == "synthetic" for record in records) / max(1, len(records))}

