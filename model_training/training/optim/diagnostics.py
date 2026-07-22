def optimizer_diagnostics(optimizer):
    states = optimizer.muon.state.values() if getattr(optimizer, "muon", None) else []
    return {
        "muon_parameter_count": len(getattr(optimizer.partition, "muon_names", [])),
        "adamw_parameter_count": len(getattr(optimizer.partition, "adamw_names", [])),
        "muon_update_norm_mean": sum(state.get("update_norm", 0.0) for state in states) / max(1, len(states)),
        "nan_inf_events": 0,
    }

