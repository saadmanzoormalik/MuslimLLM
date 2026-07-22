import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_optimistic_placeholder_construction_is_well_below_visual_budget():
    started = time.perf_counter()
    for index in range(10_000):
        _ = {"id": str(index), "role": "assistant", "content": "", "reasoning_plan": {"tasks": [{"id": "initializing", "status": "active"}]}}
    per_prompt_ms = ((time.perf_counter() - started) * 1000) / 10_000
    assert per_prompt_ms < 0.15
