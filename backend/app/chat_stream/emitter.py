from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


TASK_EVENTS = {"reasoning_task_started", "reasoning_task_completed", "reasoning_task_skipped", "reasoning_task_failed"}


class StreamEmitter:
    def __init__(self, *, request_id: str, chat_id: str, assistant_message_id: str):
        self.request_id = request_id
        self.chat_id = chat_id
        self.assistant_message_id = assistant_message_id
        self.sequence = 0

    def event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        self.sequence += 1
        envelope: dict[str, Any] = {
            **payload,
            "type": event_type,
            "request_id": self.request_id,
            "chat_id": self.chat_id,
            "assistant_message_id": self.assistant_message_id,
            "sequence": self.sequence,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if event_type in TASK_EVENTS:
            status = "skipped" if event_type == "reasoning_task_skipped" else payload.get("status")
            envelope["task"] = {
                "id": payload.get("task_id"),
                "label": payload.get("label"),
                "kind": payload.get("kind", "analysis"),
                "status": status,
                "started_at": payload.get("started_at"),
                "completed_at": payload.get("completed_at"),
            }
        return envelope

    def sse(self, event_type: str, payload: dict[str, Any] | None = None) -> str:
        event = self.event(event_type, payload)
        return f"event: {event_type}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

