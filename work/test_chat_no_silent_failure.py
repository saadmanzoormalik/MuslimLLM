from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend/app/page.tsx").read_text(encoding="utf-8")


def test_empty_model_output_cannot_complete_silently():
    assert 'raise RuntimeError("Model returned an empty response.")' in MAIN
    assert "if assistant_content.strip():" in MAIN
    assert 'yield emit("error", failure_payload)' in MAIN
    assert "Something went wrong. Please retry." in PAGE
