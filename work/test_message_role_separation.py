from pathlib import Path

from backend.app.imports.normalizer import normalize_messages


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend/app/page.tsx").read_text()
RENDERER = (ROOT / "frontend/components/chat/MessageRenderer.tsx").read_text()
USER = (ROOT / "frontend/components/chat/UserMessage.tsx").read_text()
ASSISTANT = (ROOT / "frontend/components/chat/AssistantMessage.tsx").read_text()
BACKEND = (ROOT / "backend/app/main.py").read_text()


def test_role_components_are_structurally_separate():
    assert 'data-message-role="user"' in USER
    assert 'aria-label="You said"' in USER
    assert 'data-message-role="assistant"' in ASSISTANT
    assert 'aria-label="Muslim LLM responded"' in ASSISTANT
    assert "<UserMessage" in RENDERER
    assert "<AssistantMessage" in RENDERER
    assert "<MarkdownMessage content={content}" in ASSISTANT
    assert "<MarkdownMessage" not in USER


def test_streaming_updates_are_id_targeted():
    assert "updateAssistantMessage(prev, assistantMessageId" in PAGE
    assert "next[next.length - 1]" not in PAGE
    assert "key={message.id}" in PAGE
    assert 'message.role === "assistant"' in PAGE


def test_database_records_remain_role_safe():
    assert "values (%s,%s,'user',%s" in BACKEND
    assert "values (%s,%s,'assistant',''" in BACKEND
    assert "where id=%s and chat_id=%s and role='assistant'" in BACKEND
    assert "assistant_content = user_content" not in BACKEND


def test_imported_messages_preserve_boundaries():
    source = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"},
        {"role": "system", "content": "Imported system context"},
        {"role": "tool", "content": "Tool result"},
    ]
    normalized = normalize_messages(source)
    assert [message["role"] for message in normalized] == ["user", "assistant", "system", "tool"]
    assert [message["content"] for message in normalized] == ["Question", "Answer", "Imported system context", "Tool result"]


if __name__ == "__main__":
    test_role_components_are_structurally_separate()
    test_streaming_updates_are_id_targeted()
    test_database_records_remain_role_safe()
    test_imported_messages_preserve_boundaries()
    print("message role separation checks passed")
