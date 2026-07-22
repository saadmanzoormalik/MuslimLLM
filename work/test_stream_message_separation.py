import json
import os
from uuid import uuid4

import httpx


API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")


def parse_sse(response: httpx.Response) -> list[tuple[str, dict]]:
    events = []
    event_name = "message"
    data_line = None
    for line in response.iter_lines():
        if line.startswith("event: "):
            event_name = line[7:]
        elif line.startswith("data: "):
            data_line = line[6:]
        elif not line and data_line is not None:
            events.append((event_name, json.loads(data_line)))
            event_name = "message"
            data_line = None
    return events


def submit(prompt: str, *, chat_id: str | None = None, reuse_user_message_id: str | None = None):
    identifiers = {
        "request_id": str(uuid4()),
        "user_message_id": reuse_user_message_id or str(uuid4()),
        "assistant_message_id": str(uuid4()),
    }
    payload = {
        "message": prompt,
        "chat_id": chat_id,
        "model": "muslim-llm-core",
        "stream": True,
        "reasoning_depth": "quick",
        **identifiers,
    }
    if reuse_user_message_id:
        payload["reuse_user_message_id"] = reuse_user_message_id
    with httpx.stream("POST", f"{API_BASE}/chat", json=payload, timeout=240) as response:
        response.raise_for_status()
        return identifiers, parse_sse(response)


def test_stream_and_retry_keep_roles_separate():
    prompt = "What are the major causes of inflation?"
    first_ids, first_events = submit(prompt)
    assert first_events
    assert all(payload.get("assistant_message_id") == first_ids["assistant_message_id"] for _, payload in first_events)

    meta = next(payload for name, payload in first_events if name == "meta")
    complete = next(payload for name, payload in first_events if name == "complete")
    chat_id = meta["chat_id"]
    assert meta["user_message"] == {"id": first_ids["user_message_id"], "role": "user", "content": prompt}
    assert meta["assistant_message"]["role"] == "assistant"
    assert meta["assistant_message"]["content"] == ""
    assert complete["assistant_message"]["content"].strip()
    assert not complete["assistant_message"]["content"].strip().startswith(prompt)

    token_events = [payload for name, payload in first_events if name == "token"]
    assert token_events
    assert all("user_message" not in payload and "user_message_id" not in payload for payload in token_events)

    try:
        chat = httpx.get(f"{API_BASE}/chats/{chat_id}", timeout=30).json()
        user_rows = [message for message in chat["messages"] if message["role"] == "user" and message["content"] == prompt]
        assistant_rows = [message for message in chat["messages"] if message["role"] == "assistant"]
        assert len(user_rows) == 1
        assert user_rows[0]["id"] != assistant_rows[-1]["id"]
        assert prompt not in assistant_rows[-1]["content"][: len(prompt) + 1]

        retry_ids, retry_events = submit(prompt, chat_id=chat_id, reuse_user_message_id=first_ids["user_message_id"])
        assert retry_ids["assistant_message_id"] != first_ids["assistant_message_id"]
        assert all(payload.get("assistant_message_id") == retry_ids["assistant_message_id"] for _, payload in retry_events)

        retried_chat = httpx.get(f"{API_BASE}/chats/{chat_id}", timeout=30).json()
        retried_user_rows = [message for message in retried_chat["messages"] if message["role"] == "user" and message["content"] == prompt]
        assert len(retried_user_rows) == 1
    finally:
        httpx.delete(f"{API_BASE}/chats/{chat_id}", timeout=30)


if __name__ == "__main__":
    test_stream_and_retry_keep_roles_separate()
    print("stream message separation checks passed")
