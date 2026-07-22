from evaluation.release_gate import evaluate_release


def test_release_gate_blocks_collapsed_experts():
    report = {"initial_loss": 5, "final_loss": 4, "metrics": [{"routing": [{"dead_expert_count": 2, "dominant_expert_share": .9, "dropped_token_rate": 0, "expert_entropy": .2}]}]}
    result = evaluate_release(report)
    assert not result["passed"] and "dead_experts" in result["failures"]


def test_release_gate_allows_balanced_stage0():
    metric = {"dead_expert_count": 0, "dominant_expert_share": .3, "dropped_token_rate": 0, "expert_entropy": .9}
    assert evaluate_release({"initial_loss": 5, "final_loss": 4.9, "metrics": [{"routing": [metric]}, {"routing": [metric]}]})["passed"]

