import torch
from torch import nn

from .dispatch import dispatch_and_combine
from .experts import RoutedExperts
from .load_balance import load_balance_loss, router_z_loss
from .metrics import routing_metrics
from .router import TopKRouter
from .shared_experts import SharedExperts


class MoELayer(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.router = TopKRouter(config.hidden_size, config.num_routed_experts, config.experts_per_token, config.router_temperature, config.router_jitter)
        self.experts = RoutedExperts(config.num_routed_experts, config.hidden_size, config.expert_intermediate_size, config.expert_dropout)
        self.shared = SharedExperts(config.num_shared_experts, config.hidden_size, config.expert_intermediate_size, config.expert_dropout, config.shared_expert_weight)
        self.last_metrics: dict[str, float] = {}

    def forward(self, x: torch.Tensor, deterministic: bool = False):
        shape = x.shape
        tokens = x.reshape(-1, shape[-1])
        routing = self.router(tokens, deterministic)
        routed, dropped, overflow = dispatch_and_combine(tokens, routing, self.experts, self.config.expert_capacity_factor, self.config.token_drop_enabled)
        output = routed.view(shape) + self.shared(x)
        balance = load_balance_loss(routing.probabilities, routing.indices, self.config.num_routed_experts)
        z_loss = router_z_loss(routing.logits)
        auxiliary = self.config.load_balance_loss_coefficient * balance + self.config.router_z_loss_coefficient * z_loss
        self.last_metrics = routing_metrics(routing.probabilities.detach(), routing.indices.detach(), self.config.num_routed_experts, dropped, overflow)
        self.last_metrics.update({"load_balance_loss": balance.item(), "router_z_loss": z_loss.item(), "shared_expert_contribution": float(self.config.num_shared_experts > 0)})
        return output, auxiliary

