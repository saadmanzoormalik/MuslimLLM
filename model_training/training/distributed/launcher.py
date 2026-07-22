import os

import torch.distributed as dist


def initialize_distributed(backend: str | None = None):
    world_size = int(os.getenv("WORLD_SIZE", "1"))
    if world_size > 1 and not dist.is_initialized():
        dist.init_process_group(backend=backend or ("nccl" if os.getenv("CUDA_VISIBLE_DEVICES") else "gloo"))
    return {"rank": int(os.getenv("RANK", "0")), "world_size": world_size, "local_rank": int(os.getenv("LOCAL_RANK", "0"))}

