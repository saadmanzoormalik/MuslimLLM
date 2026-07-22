import torch

from .muon import Muon
from .parameter_groups import partition_parameters


class HybridOptimizer:
    def __init__(self, muon: Muon | None, adamw: torch.optim.AdamW | None, partition):
        self.muon, self.adamw, self.partition = muon, adamw, partition

    @property
    def param_groups(self):
        return (self.muon.param_groups if self.muon else []) + (self.adamw.param_groups if self.adamw else [])

    def zero_grad(self, set_to_none=True):
        if self.muon: self.muon.zero_grad(set_to_none=set_to_none)
        if self.adamw: self.adamw.zero_grad(set_to_none=set_to_none)

    def step(self):
        if self.muon: self.muon.step()
        if self.adamw: self.adamw.step()

    def state_dict(self):
        return {"muon": self.muon.state_dict() if self.muon else None, "adamw": self.adamw.state_dict() if self.adamw else None, "muon_names": self.partition.muon_names, "adamw_names": self.partition.adamw_names}

    def load_state_dict(self, state):
        if self.muon and state["muon"]: self.muon.load_state_dict(state["muon"])
        if self.adamw and state["adamw"]: self.adamw.load_state_dict(state["adamw"])


def build_hybrid_optimizer(model, *, muon_lr=0.02, adamw_lr=3e-4, minimum_matrix_elements=4096, router_on_muon=False, weight_decay=0.1):
    partition = partition_parameters(model, minimum_matrix_elements, router_on_muon)
    muon = Muon(partition.muon, lr=muon_lr, weight_decay=weight_decay) if partition.muon else None
    adamw = torch.optim.AdamW(partition.adamw, lr=adamw_lr, weight_decay=weight_decay) if partition.adamw else None
    return HybridOptimizer(muon, adamw, partition)

