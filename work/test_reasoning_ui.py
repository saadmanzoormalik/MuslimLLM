from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend/app/page.tsx").read_text()

for component in ["ReasoningProcess", "ReasoningTask", "ReasoningSummary", "ThinkingIndicator"]:
    assert (ROOT / f"frontend/components/chat/{component}.tsx").exists()

process = (ROOT / "frontend/components/chat/ReasoningProcess.tsx").read_text()
assert "Thinking" in process
assert "Reasoning ·" in process
assert 'aria-live="polite"' in process
assert "LiveReasoningDock" not in PAGE
assert "ReasoningPanel" not in PAGE
assert all(label in PAGE for label in ['"quick"', '"standard"', '"deep"'])
assert "localStorage" in PAGE
assert "reasoning_depth" in PAGE

print("reasoning UI contract checks passed")
