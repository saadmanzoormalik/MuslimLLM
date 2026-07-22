import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.reasoning.classifier import classify_reasoning_request
from app.reasoning.task_planner import create_reasoning_plan


async def run():
    general = classify_reasoning_request("Explain why leaves change color.", [], {})
    science = classify_reasoning_request("Explain evolution using modern biology.", [], {})
    values = classify_reasoning_request("How should I handle gossip among friends?", [], {"values_sensitive": True})
    fiqh = classify_reasoning_request(
        "Does my zakat calculation differ by madhab?",
        [],
        {"query_is_islamic": True, "madhab_sensitive": True, "fatwa_sensitive": True},
    )
    complex_case = classify_reasoning_request(
        "Compare multiple approaches, analyze the trade-offs, and give a step by step plan for this complex decision? What could fail?",
        [],
        {},
    )

    general_plan = await create_reasoning_plan("General", [], [], general, request_id="general")
    science_plan = await create_reasoning_plan("Science", [], [], science, request_id="science")
    values_plan = await create_reasoning_plan("Values", [], [], values, request_id="values")
    fiqh_plan = await create_reasoning_plan("Fiqh", [], ["local_sources"], fiqh, request_id="fiqh", depth="deep")
    quick_plan = await create_reasoning_plan("Complex", [], [], complex_case, request_id="quick", depth="quick")
    deep_plan = await create_reasoning_plan("Complex", [], [], complex_case, request_id="deep", depth="deep")
    complex_standard_plan = await create_reasoning_plan("Complex", [], [], complex_case, request_id="complex-standard", depth="standard")

    assert general_plan.mode == "general"
    assert "sources" not in {task.id for task in science_plan.tasks}
    assert "madhab" not in {task.id for task in science_plan.tasks}
    assert "values" in {task.id for task in values_plan.tasks}
    assert {"sources", "madhab", "personal_context"}.issubset({task.id for task in fiqh_plan.tasks})
    assert len(quick_plan.tasks) < len(deep_plan.tasks)
    assert len(general_plan.tasks) < len(complex_standard_plan.tasks)
    assert "uncertainty" in {task.id for task in deep_plan.tasks}
    assert "assumptions" in {task.id for task in deep_plan.tasks}


if __name__ == "__main__":
    asyncio.run(run())
    print("dynamic reasoning classification checks passed")
