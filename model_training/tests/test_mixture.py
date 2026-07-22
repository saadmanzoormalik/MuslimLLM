from training.data.mixture import mixture_metrics, sample_mixture
from training.data.mixture_optimizer import competence_aware_weights
from training.data.registry import DataRecord


def make(domain, origin="human"):
    return DataRecord(domain, "public-domain", "en", domain, domain, "public-domain", "primary", origin=origin, generation_model="test" if origin == "synthetic" else None)


def test_mixture_caps_synthetic_and_is_reproducible():
    records = [make("general") for _ in range(3)] + [make("islamic", "synthetic") for _ in range(3)]
    first = sample_mixture(records, {"general": .5, "islamic": .5}, 20, 7, synthetic_cap=.2)
    second = sample_mixture(records, {"general": .5, "islamic": .5}, 20, 7, synthetic_cap=.2)
    assert [r.source for r in first] == [r.source for r in second]
    assert mixture_metrics(first)["synthetic_ratio"] <= .2


def test_competence_weights_normalize():
    weights = competence_aware_weights({"general": 1, "arabic": 2, "fiqh": 3})
    assert abs(sum(weights.values()) - 1) < 1e-9 and weights["fiqh"] > weights["general"]

