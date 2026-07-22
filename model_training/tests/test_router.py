import torch

from training.model.moe.router import TopKRouter


def test_router_probabilities_and_topk_are_valid():
    router = TopKRouter(16, 6, 2)
    route = router(torch.randn(20, 16), deterministic=True)
    assert torch.allclose(route.probabilities.sum(-1), torch.ones(20), atol=1e-6)
    assert route.indices.shape == (20, 2)
    assert torch.allclose(route.weights.sum(-1), torch.ones(20), atol=1e-6)


def test_deterministic_router_repeats():
    router = TopKRouter(8, 4, 1, jitter=0.2).train()
    tokens = torch.randn(5, 8)
    assert torch.equal(router(tokens, True).indices, router(tokens, True).indices)

