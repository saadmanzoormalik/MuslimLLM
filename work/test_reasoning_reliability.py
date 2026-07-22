import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.reasoning.task_events import task_failed, task_started
from app.reasoning.task_planner import fallback_reasoning_plan
from app.reasoning.validation import validate_answer

plan = fallback_reasoning_plan("fallback", "standard")
assert [task.id for task in plan.tasks] == ["understand", "reason", "write", "validate"]
assert task_started(plan, "reason")["status"] == "active"
failure = task_failed(plan, "reason", "TimeoutError")
assert failure["status"] == "failed"
assert failure["error_class"] == "TimeoutError"

valid = validate_answer("Supported [1].", [{"title": "Source"}])
invalid = validate_answer("Unsupported [2].", [{"title": "Source"}])
assert valid["citations_consistent"] is True
assert invalid["citations_consistent"] is False

env_example = (ROOT / ".env.example").read_text()
for key in [
    "REASONING_PLAN_TIMEOUT_SECONDS=10",
    "REASONING_TASK_STALL_SECONDS=30",
    "REASONING_HEARTBEAT_SECONDS=5",
    "REASONING_MAX_VISIBLE_TASKS=8",
    "REASONING_SUMMARY_ENABLED=true",
]:
    assert key in env_example

print("reasoning reliability checks passed")
