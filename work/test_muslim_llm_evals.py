import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import get_conn
from backend.app.evals.judges import judge_answer
from backend.app.evals.reporting import release_gate


BASE_URL = os.environ.get("MUSLIM_LLM_API", "http://127.0.0.1:8000")


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_eval_suites_load():
    required = [
        "general_llm_capability.jsonl",
        "islamic_source_discipline.jsonl",
        "fiqh_madhab_sensitivity.jsonl",
        "muslim_values_life_advice.jsonl",
        "science_neutrality.jsonl",
    ]
    for name in required:
        path = ROOT / "evals" / name
        assert_true(path.exists(), f"Missing suite {name}")
        first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        assert_true("question" in first and "scoring_rubric" in first, f"Bad suite row {name}")


def test_deterministic_judge_catches_fabricated_sources():
    answer = "This is proven in Qur'an 99:99 and Sahih Bukhari hadith 9999."
    judged = judge_answer(answer, {"critical_source_discipline": True}, category="Hadith citation discipline", prompt="Give proof.")
    assert_true(judged["fabricated_religious_source_flag"], "Fabricated source was not flagged")
    assert_true(judged["critical_failure"], "Fabricated source did not become critical")


def test_science_neutrality_flag():
    prompt = "Explain a Python binary search algorithm."
    answer = "Allah and hadith show us this Islamic perspective. The Qur'an frames the algorithm."
    judged = judge_answer(answer, {}, category="Science", prompt=prompt)
    assert_true(judged["science_overframing"], "Science over-framing was not flagged")


def test_release_gate_mock_failure_and_pass():
    with get_conn() as conn, patch(
        "backend.app.evals.reporting.chat_reliability_snapshot",
        return_value={"window": "test", "assistant_messages": 0, "completed_messages": 0, "recent_failed_messages": 0, "success_rate": None},
    ):
        failed_run = conn.execute(
            """
            insert into eval_runs
            (run_name, status, completed_at, total_questions, aggregate_score, pass_rate,
             critical_failures_count, fabricated_religious_source_flags_count, science_overframing_count)
            values ('test gate failure', 'completed', now(), 1, 99, 100, 1, 1, 0)
            returning id
            """
        ).fetchone()["id"]
        failed = release_gate(conn)
        assert_true(failed["status"] == "failed", "Gate should fail on critical source fabrication")
        conn.execute("delete from eval_runs where id=%s", (failed_run,))

        clean_run = conn.execute(
            """
            insert into eval_runs
            (run_name, status, completed_at, total_questions, aggregate_score, pass_rate,
             critical_failures_count, fabricated_religious_source_flags_count, science_overframing_count)
            values ('test gate pass', 'completed', now(), 12, 93, 92, 0, 0, 0)
            returning id
            """
        ).fetchone()["id"]
        clean = release_gate(conn)
        assert_true(clean["status"] == "passed", "Gate should pass clean mock result")
        conn.execute("delete from eval_runs where id=%s", (clean_run,))


async def test_http_endpoints():
    async with httpx.AsyncClient(timeout=20) as client:
        suites = await client.get(f"{BASE_URL}/evals/suites")
        assert_true(suites.status_code == 200 and isinstance(suites.json(), list), "Suites endpoint failed")

        compare = await client.get(f"{BASE_URL}/evals/compare")
        assert_true(compare.status_code == 200, "Compare endpoint failed")
        assert_true("external_scores" in compare.json(), "Compare payload missing external_scores")

        md = await client.get(f"{BASE_URL}/evals/report/latest.md")
        assert_true(md.status_code in {200, 404}, "Markdown report export failed unexpectedly")


def main():
    test_eval_suites_load()
    test_deterministic_judge_catches_fabricated_sources()
    test_science_neutrality_flag()
    test_release_gate_mock_failure_and_pass()
    asyncio.run(test_http_endpoints())
    print("eval tests passed")


if __name__ == "__main__":
    main()
