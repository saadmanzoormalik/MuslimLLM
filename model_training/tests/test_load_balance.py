import torch

from training.model.moe.load_balance import load_balance_loss


def test_load_balance_loss_backpropagates():
    logits = torch.randn(12, 4, requires_grad=True)
    probabilities = logits.softmax(-1)
    indices = probabilities.topk(2, dim=-1).indices
    load_balance_loss(probabilities, indices, 4).backward()
    assert logits.grad is not None and torch.isfinite(logits.grad).all()

