from dataclasses import dataclass


@dataclass
class ParameterPartition:
    muon: list
    adamw: list
    muon_names: list[str]
    adamw_names: list[str]


def partition_parameters(model, minimum_matrix_elements: int = 4096, router_on_muon: bool = False) -> ParameterPartition:
    muon, adamw, muon_names, adamw_names = [], [], [], []
    excluded = ("embedding", "lm_head", "norm")
    for name, parameter in model.named_parameters():
        router_excluded = "router" in name and not router_on_muon
        eligible = parameter.ndim == 2 and parameter.numel() >= minimum_matrix_elements and not any(part in name for part in excluded) and not router_excluded
        (muon if eligible else adamw).append(parameter)
        (muon_names if eligible else adamw_names).append(name)
    return ParameterPartition(muon, adamw, muon_names, adamw_names)

