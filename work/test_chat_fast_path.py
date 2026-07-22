import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.chat_stream.routing import deterministic_instant_answer, route_request
from app.main import is_values_sensitive_query
from app.alignment import alignment_guardrail_response
from app.reasoning.classifier import classify_reasoning_request
from app.reasoning.task_planner import create_reasoning_plan


def test_instant_path_is_deterministic_and_skips_retrieval():
    route = route_request("What is 2 + 2?", requested_mode="auto", islamic=False, fiqh=False, values_sensitive=False)
    assert route.name == "instant"
    assert route.retrieval_required is False
    assert deterministic_instant_answer("What is 2 + 2?") == "4"


def test_quick_tasks_preserve_domain_relevance_without_fake_retrieval():
    classification = classify_reasoning_request("What is photosynthesis?", [], {})
    classification.update({"route": "quick", "retrieval_required": False})
    plan = asyncio.run(create_reasoning_plan("What is photosynthesis?", [], [], classification, request_id="science", depth="quick"))
    task_ids = {task.id for task in plan.tasks}
    assert "concepts" in task_ids
    assert "sources" not in task_ids
    assert len(plan.tasks) <= 5


def test_values_task_survives_fast_mode():
    assert is_values_sensitive_query("Can I lie to close an important sale?") is True
    classification = classify_reasoning_request("Can I lie to close an important sale?", [], {"values_sensitive": True})
    classification.update({"route": "quick", "retrieval_required": False})
    plan = asyncio.run(create_reasoning_plan("Can I lie to close an important sale?", [], [], classification, request_id="values", depth="quick"))
    assert "values" in {task.id for task in plan.tasks}


def test_travel_prayer_has_cautious_deterministic_floor():
    answer = alignment_guardrail_response("How should a traveler pray?") or ""
    assert "differ among the madhhabs" in answer
    assert "qualified local scholar" in answer
