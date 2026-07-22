from __future__ import annotations


DEFAULT_THRESHOLDS = {"loss_reduction_min": 0.0, "dead_experts_max": 0, "dominant_expert_share_max": 0.75, "dropped_token_rate_max": 0.01, "expert_entropy_min": 0.45, "empty_response_rate_max": 0.0}


def evaluate_release(report: dict, *, thresholds=None, required_artifacts=None):
    thresholds = thresholds or DEFAULT_THRESHOLDS
    failures = []
    if report.get("initial_loss", 0) - report.get("final_loss", 0) < thresholds["loss_reduction_min"]: failures.append("learning_curve")
    routing = [metric for row in report.get("metrics", []) for metric in row.get("routing", [])]
    if routing:
        if max(item["dead_expert_count"] for item in routing[-2:]) > thresholds["dead_experts_max"]: failures.append("dead_experts")
        if max(item["dominant_expert_share"] for item in routing[-2:]) > thresholds["dominant_expert_share_max"]: failures.append("dominant_expert")
        if max(item["dropped_token_rate"] for item in routing) > thresholds["dropped_token_rate_max"]: failures.append("dropped_tokens")
        if min(item["expert_entropy"] for item in routing[-2:]) < thresholds["expert_entropy_min"]: failures.append("expert_entropy")
    for artifact in required_artifacts or []:
        if not artifact.exists(): failures.append(f"missing:{artifact.name}")
    return {"status": "Architecture validated" if not failures else "Experimental", "passed": not failures, "failures": failures, "thresholds": thresholds}

