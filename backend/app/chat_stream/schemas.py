from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ChatEventType = Literal[
    "accepted", "reasoning_plan", "reasoning_task_started", "reasoning_task_completed",
    "reasoning_task_skipped", "reasoning_task_failed", "status", "token", "source",
    "warning", "heartbeat", "reasoning_summary", "metadata", "error", "complete",
]


class ChatStreamEvent(BaseModel):
    request_id: str
    chat_id: str
    assistant_message_id: str
    sequence: int = Field(ge=1)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    type: ChatEventType
    task: dict[str, Any] | None = None
    content: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

