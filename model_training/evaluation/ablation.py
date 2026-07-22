from pathlib import Path
import json
import statistics

from training.trainer import train_experiment


def run_stage0_matrix(root: Path, steps: int = 12, seeds=(17, 29, 43)):
    matrix = [
        ("dense_adamw", "unit_dense.yaml", "adamw"),
        ("dense_hybrid", "unit_dense.yaml", "hybrid"),
        ("moe_adamw", "unit_moe.yaml", "adamw"),
        ("moe_hybrid", "unit_moe.yaml", "hybrid"),
        ("shared_moe_hybrid", "unit_moe_shared.yaml", "hybrid"),
    ]
    results = {name: [] for name, _, _ in matrix}
    for name, config, optimizer in matrix:
        for seed in seeds:
            report = train_experiment(root / "configs/model" / config, root / "experiments" / f"{name}-seed-{seed}", steps=steps, optimizer_type=optimizer, seed=seed)
            results[name].append(report)
    summary = {}
    for name, reports in results.items():
        reductions = [report["initial_loss"] - report["final_loss"] for report in reports]
        throughput = [report["tokens_per_second"] for report in reports]
        summary[name] = {
            "seeds": list(seeds),
            "mean_loss_reduction": statistics.mean(reductions),
            "loss_reduction_stdev": statistics.stdev(reductions),
            "mean_tokens_per_second": statistics.mean(throughput),
            "throughput_stdev": statistics.stdev(throughput),
            "parameter_counts": reports[0]["parameter_counts"],
        }
    (root / "experiments/stage0-ablation.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
