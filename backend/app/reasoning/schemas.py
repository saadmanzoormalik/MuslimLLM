from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ReasoningMode = Literal["general", "research", "science", "technical", "values_sensitive", "islamic_knowledge", "fiqh_sensitive", "contextual"]
ReasoningDepth = Literal["quick", "standard", "deep"]
TaskStatus = Literal["pending", "active", "completed", "skipped", "failed"]
TaskKind = Literal["analysis", "retrieval", "tool", "validation", "generation"]


@dataclass
class ReasoningTask:
    id: str
    label: str
    status: TaskStatus = "pending"
    kind: TaskKind = "analysis"
    started_at: str | None = None
    completed_at: str | None = None

    def public(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "kind": self.kind,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class ReasoningPlan:
    request_id: str
    mode: ReasoningMode
    depth: ReasoningDepth
    tasks: list[ReasoningTask] = field(default_factory=list)

    def task(self, task_id: str) -> ReasoningTask | None:
        return next((task for task in self.tasks if task.id == task_id), None)

    def public(self) -> dict:
        return {
            "request_id": self.request_id,
            "mode": self.mode,
            "depth": self.depth,
            "tasks": [task.public() for task in self.tasks],
        }
