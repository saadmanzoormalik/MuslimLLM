from torch import nn

from ..dense_ffn import SwiGLUFFN


class RoutedExperts(nn.ModuleList):
    def __init__(self, count: int, hidden: int, intermediate: int, dropout: float):
        super().__init__([SwiGLUFFN(hidden, intermediate, dropout) for _ in range(count)])

