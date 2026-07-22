def competence_aware_weights(validation_losses: dict[str, float], floor: float = 0.05, cap: float = 0.4):
    total = sum(max(0.0, value) for value in validation_losses.values()) or 1.0
    raw = {domain: max(floor, min(cap, loss / total)) for domain, loss in validation_losses.items()}
    normalizer = sum(raw.values())
    return {domain: value / normalizer for domain, value in raw.items()}

