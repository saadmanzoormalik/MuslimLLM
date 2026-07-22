from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend/app/page.tsx").read_text(encoding="utf-8")


def test_duplicate_submission_and_cancellation_are_guarded():
    assert "submittingRef.current" in PAGE
    assert "new AbortController()" in PAGE
    assert "abortRef.current?.abort()" in PAGE
    assert 'content: message.content || "Generation stopped."' in PAGE
