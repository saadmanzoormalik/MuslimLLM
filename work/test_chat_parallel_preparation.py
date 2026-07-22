from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")


def test_required_retrieval_starts_before_planning_completes():
    retrieval = MAIN.index("retrieval_future = asyncio.create_task")
    planning = MAIN.index("plan = await asyncio.wait_for", retrieval)
    await_retrieval = MAIN.index("citations = await retrieval_future", planning)
    assert retrieval < planning < await_retrieval
