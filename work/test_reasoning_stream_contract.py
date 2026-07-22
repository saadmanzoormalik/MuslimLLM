import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.chat_stream.emitter import StreamEmitter
from app.chat_stream.schemas import ChatStreamEvent


def test_canonical_envelope_is_monotonic_and_role_safe():
    emitter = StreamEmitter(request_id="req", chat_id="chat", assistant_message_id="assistant")
    accepted = emitter.event("accepted", {"label": "Preparing your answer"})
    started = emitter.event("reasoning_task_started", {"task_id": "understand", "label": "Understanding", "status": "active"})
    token = emitter.event("token", {"content": "Hello"})
    complete = emitter.event("complete", {"status": "completed"})
    events = [accepted, started, token, complete]
    assert [event["sequence"] for event in events] == [1, 2, 3, 4]
    assert all(event["assistant_message_id"] == "assistant" for event in events)
    assert started["task"]["id"] == "understand"
    assert token["content"] == "Hello"
    for event in events:
        ChatStreamEvent(**event)


def test_sse_frame_flushes_as_one_complete_event():
    emitter = StreamEmitter(request_id="req", chat_id="chat", assistant_message_id="assistant")
    frame = emitter.sse("accepted", {"label": "Preparing"})
    assert frame.startswith("event: accepted\ndata: ")
    assert frame.endswith("\n\n")
    payload = json.loads(frame.split("data: ", 1)[1])
    assert payload["sequence"] == 1
