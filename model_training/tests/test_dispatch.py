import torch
from torch import nn

from training.model.moe.dispatch import dispatch_and_combine
from training.model.moe.router import TopKRouter


def test_dispatch_combine_preserves_order_for_identity_experts():
    tokens = torch.randn(10, 8)
    route = TopKRouter(8, 3, 1)(tokens, deterministic=True)
    output, dropped, _ = dispatch_and_combine(tokens, route, nn.ModuleList([nn.Identity() for _ in range(3)]), 10, False)
    assert output.shape == tokens.shape and dropped == 0
    assert torch.allclose(output, tokens, atol=1e-6)


def test_capacity_reports_overflow():
    tokens = torch.randn(20, 4)
    router = TopKRouter(4, 2, 1)
    with torch.no_grad(): router.projection.weight.zero_()
    route = router(tokens, deterministic=True)
    _, _, overflow = dispatch_and_combine(tokens, route, nn.ModuleList([nn.Identity(), nn.Identity()]), .1, False)
    assert overflow > 0

