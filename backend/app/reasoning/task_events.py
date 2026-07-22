from __future__ import annotations

from datetime import UTC, datetime

from .schemas import ReasoningPlan


def plan_event(plan: ReasoningPlan) -> dict:
    return {"type": "reasoning_plan", **plan.public()}


def task_started(plan: ReasoningPlan, task_id: str) -> dict | None:
    task = plan.task(task_id)
    if not task or task.status not in {"pending", "failed"}:
        return None
    task.status = "active"
    task.started_at = datetime.now(UTC).isoformat()
    return {"type": "reasoning_task_started", "request_id": plan.request_id, "task_id": task.id, "label": task.label, "status": task.status, "kind": task.kind, "started_at": task.started_at}


def task_updated(plan: ReasoningPlan, task_id: str, label: str) -> dict | None:
    task = plan.task(task_id)
    if not task:
        return None
    task.label = label
    return {"type": "reasoning_task_updated", "request_id": plan.request_id, "task_id": task.id, "label": task.label, "status": task.status, "kind": task.kind}


def task_completed(plan: ReasoningPlan, task_id: str, label: str | None = None) -> dict | None:
    task = plan.task(task_id)
    if not task:
        return None
    task.status = "completed"
    if label:
        task.label = label
    task.completed_at = datetime.now(UTC).isoformat()
    return {"type": "reasoning_task_completed", "request_id": plan.request_id, "task_id": task.id, "label": task.label, "status": task.status, "kind": task.kind, "completed_at": task.completed_at}


def task_failed(plan: ReasoningPlan, task_id: str, error_class: str, *, skipped: bool = False) -> dict | None:
    task = plan.task(task_id)
    if not task:
        return None
    task.status = "skipped" if skipped else "failed"
    task.completed_at = datetime.now(UTC).isoformat()
    return {"type": "reasoning_task_failed", "request_id": plan.request_id, "task_id": task.id, "label": task.label, "status": task.status, "kind": task.kind, "error_class": error_class, "completed_at": task.completed_at}
