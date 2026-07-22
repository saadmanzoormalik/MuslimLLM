from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = (ROOT / "backend/app/main.py").read_text()
PAGE = (ROOT / "frontend/app/page.tsx").read_text()
ASSISTANT = (ROOT / "frontend/components/chat/AssistantMessage.tsx").read_text()
REASONING = (ROOT / "frontend/components/chat/ReasoningProcess.tsx").read_text()


def test_reasoning_events_are_bound_to_assistant_id():
    assert '"assistant_message_id": run.message_id' in BACKEND
    assert "return sse(event, role_safe_payload)" in BACKEND
    assert "yield emit(\"reasoning_plan\"" in BACKEND
    assert "yield emit(\"reasoning_summary\"" in BACKEND
    assert "data.assistant_message_id !== assistantMessageId" in PAGE


def test_reasoning_is_outside_answer_markdown():
    reasoning_position = ASSISTANT.index("<ReasoningProcess")
    markdown_position = ASSISTANT.index("<MarkdownMessage")
    assert reasoning_position < markdown_position
    assert 'aria-label="Reasoning process"' in REASONING
    token_handler = PAGE[PAGE.index('if (eventName === "token")'):PAGE.index('if (eventName === "reasoning_summary")')]
    assert "content: message.content +" in token_handler
    assert "reasoning_summary" not in token_handler


def test_prompt_is_not_used_to_initialize_assistant_content():
    assert 'content: ""' in PAGE
    assert "assistant_content = \"\"" in BACKEND
    assert "assistant_content = user_content" not in BACKEND
    assert "Do not prepend, quote, or restate the user's full question" in BACKEND


if __name__ == "__main__":
    test_reasoning_events_are_bound_to_assistant_id()
    test_reasoning_is_outside_answer_markdown()
    test_prompt_is_not_used_to_initialize_assistant_content()
    print("reasoning message binding checks passed")
