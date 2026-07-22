from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_chat_mounts_reasoning_component():
    page = (ROOT / "frontend/app/page.tsx").read_text(encoding="utf-8")
    renderer = (ROOT / "frontend/components/chat/MessageRenderer.tsx").read_text(encoding="utf-8")
    message = (ROOT / "frontend/components/chat/AssistantMessage.tsx").read_text(encoding="utf-8")
    process = (ROOT / "frontend/components/chat/ReasoningProcess.tsx").read_text(encoding="utf-8")
    assert "<MessageRenderer" in page
    assert "<AssistantMessage" in renderer
    assert "<ReasoningProcess" in message
    assert 'aria-live="polite"' in process
    assert "if (!active && hasContent) setExpanded(false)" in process


def test_chat_restore_orders_user_before_assistant_for_equal_timestamps():
    backend = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert "case when role='user' then 0 when role='assistant' then 1 else 2 end" in backend
