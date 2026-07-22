import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.reasoning.classifier import classify_reasoning_request
from app.reasoning.task_planner import create_reasoning_plan

FORBIDDEN = ["system prompt", "developer instruction", "private scratchpad", "chain of thought", "api key", "token budget"]


async def run():
    secret_message = "My private code is SECRET-1298. Explain this technical bug."
    classification = classify_reasoning_request(secret_message, [], {})
    plan = await create_reasoning_plan(secret_message, [], [], classification, request_id="privacy")
    public = json.dumps(plan.public()).lower()
    assert "secret-1298" not in public
    assert all(term not in public for term in FORBIDDEN)
    prompt = (ROOT / "muslim_llm_system_prompt.md").read_text().lower()
    assert "never reveal private chain-of-thought" in prompt
    assert "do not claim that sources" in prompt


if __name__ == "__main__":
    asyncio.run(run())
    print("reasoning privacy checks passed")
