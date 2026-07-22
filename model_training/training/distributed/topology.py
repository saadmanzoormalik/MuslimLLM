from dataclasses import dataclass


@dataclass(frozen=True)
class ParallelTopology:
    data: int = 1
    tensor: int = 1
    pipeline: int = 1
    expert: int = 1

    @property
    def world_size(self): return self.data * self.tensor * self.pipeline * self.expert

    def validate(self, actual_world_size: int):
        if self.world_size != actual_world_size:
            raise ValueError(f"Topology requires {self.world_size} ranks, received {actual_world_size}")

