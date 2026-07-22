import torch


def load_balance_loss(probabilities: torch.Tensor, indices: torch.Tensor, experts: int) -> torch.Tensor:
    importance = probabilities.mean(dim=0)
    assignments = torch.nn.functional.one_hot(indices[:, 0], experts).float().mean(dim=0)
    return experts * torch.sum(importance * assignments)


def router_z_loss(logits: torch.Tensor) -> torch.Tensor:
    return torch.logsumexp(logits, dim=-1).square().mean()

