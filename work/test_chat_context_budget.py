import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.chat_stream.context import select_context


def test_context_is_bounded_and_deduplicated():
    rows = [
        {"role": "user", "content": "old " * 1000},
        {"role": "assistant", "content": "same answer"},
        {"role": "assistant", "content": "same answer"},
        {"role": "user", "content": "current question"},
    ]
    selected = select_context(rows, message_limit=3, token_budget=20)
    assert selected[-1]["content"] == "current question"
    assert sum(item["content"] == "same answer" for item in selected) <= 1
    assert all("old" not in item["content"] for item in selected)
