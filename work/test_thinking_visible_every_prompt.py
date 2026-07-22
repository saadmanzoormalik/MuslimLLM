from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend/app/page.tsx").read_text(encoding="utf-8")
REASONING = (ROOT / "frontend/components/chat/ReasoningProcess.tsx").read_text(encoding="utf-8")


def test_optimistic_thinking_is_created_before_network_request():
    placeholder = PAGE.index("reasoning_plan: pendingReasoningPlan")
    render = PAGE.index("setMessages((prev)", placeholder)
    request = PAGE.index("await fetch(", render)
    assert placeholder < render < request
    assert 'id: "initializing"' in PAGE
    assert 'source: "client_optimistic"' in PAGE
    assert "Thinking" in REASONING


def test_reasoning_remains_separate_from_markdown():
    assistant = (ROOT / "frontend/components/chat/AssistantMessage.tsx").read_text(encoding="utf-8")
    assert assistant.index("<ReasoningProcess") < assistant.index("<MarkdownMessage")
