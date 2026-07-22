from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLM = (ROOT / "backend/app/llm.py").read_text(encoding="utf-8")
MAIN = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")


def test_model_uses_shared_client_queue_and_warmup():
    assert "def shared_client" in LLM
    assert "_MODEL_SEMAPHORE.acquire" in LLM
    assert '"keep_alive": LLM_KEEP_ALIVE_DURATION' in LLM
    assert "async def warmup_model" in LLM
    assert "asyncio.create_task(warmup_model())" in MAIN
