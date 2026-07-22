import torch

from training.optim.muon import Muon, newton_schulz_orthogonalize


def test_muon_updates_matrix_and_rejects_vector():
    matrix = torch.nn.Parameter(torch.randn(16, 16))
    matrix.grad = torch.randn_like(matrix)
    before = matrix.detach().clone()
    Muon([matrix], lr=0.01).step()
    assert not torch.equal(before, matrix)
    vector = torch.nn.Parameter(torch.ones(4)); vector.grad = torch.ones(4)
    try: Muon([vector]).step()
    except ValueError: pass
    else: raise AssertionError("Muon accepted a vector")


def test_orthogonalization_is_finite():
    result = newton_schulz_orthogonalize(torch.randn(12, 8))
    assert result.shape == (12, 8) and torch.isfinite(result).all()

