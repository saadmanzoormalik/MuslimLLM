import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import get_conn
from backend.app.imports.adapters import get_adapter, provider_adapters
from backend.app.imports.coverage import estimate_coverage
from backend.app.imports.models import init_import_schema
from backend.app.imports.normalizer import normalize_markdown_transcript
from backend.app.imports.privacy import redact_tokens_from_logs, scan_import_for_prompt_injection
from backend.app.imports.router import create_preview_job


FIXTURES = ROOT / "work" / "fixtures" / "imports"


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_provider_list():
    providers = provider_adapters()
    for key in ["chatgpt", "claude", "gemini", "deepseek", "grok", "qwen", "glm", "generic_json", "generic_markdown"]:
        assert_true(key in providers, f"Missing provider {key}")
    assert_true(not providers["chatgpt"].get_auth_url()["supported"], "ChatGPT API import should not be falsely claimed")


def test_chatgpt_export_parse():
    adapter = get_adapter("chatgpt")
    payload = (FIXTURES / "chatgpt_export_sample.json").read_bytes()
    normalized = adapter.parse_uploaded_export("chatgpt_export_sample.json", payload)
    assert_true(normalized["provider"] == "chatgpt", "Wrong provider")
    assert_true(len(normalized["conversations"]) == 1, "Conversation not parsed")
    assert_true(len(normalized["conversations"][0]["messages"]) == 2, "Messages not parsed")


def test_generic_markdown_parse_and_injection():
    text = (FIXTURES / "generic_markdown_chat.md").read_text(encoding="utf-8")
    normalized = normalize_markdown_transcript(text, provider="generic_markdown", title="generic_markdown_chat.md")
    assert_true(len(normalized["conversations"][0]["messages"]) == 4, "Markdown roles not parsed")
    warnings = scan_import_for_prompt_injection(text)
    assert_true(warnings, "Prompt injection was not flagged")


def test_coverage_missing_projects_files():
    data = {"conversations": [{"messages": [{"content": "hello"}], "source_id": "1"}], "projects": [], "files": [], "preferences": []}
    coverage = estimate_coverage(data)
    assert_true(coverage["overall"] < 100, "Coverage should reflect missing fields")
    assert_true(coverage["dimensions"]["Files"] < 100, "Missing files should lower coverage")


def test_redaction():
    redacted = redact_tokens_from_logs("api_key=sk-secret1234567890 bearer tokenvalue123456789")
    assert_true("[REDACTED_TOKEN]" in redacted, "Tokens not redacted")


def test_db_preview_and_confirm():
    if os.environ.get("SKIP_DB_IMPORT_TESTS") == "1":
        return
    with get_conn() as conn:
        init_import_schema(conn)
    adapter = get_adapter("generic_json")
    normalized = adapter.parse_uploaded_export("generic_project_folder_sample.json", (FIXTURES / "generic_project_folder_sample.json").read_bytes())
    preview = create_preview_job("generic_json", "file", normalized, "last_12_months", None, None, "generic_project_folder_sample.json")
    job_id = str(preview["job"]["id"])
    with get_conn() as conn:
        conversations = conn.execute("select count(*) as count from imported_conversations where import_job_id=%s", (job_id,)).fetchone()["count"]
        assert_true(conversations == 1, "Preview did not store conversation")


def main():
    test_provider_list()
    test_chatgpt_export_parse()
    test_generic_markdown_parse_and_injection()
    test_coverage_missing_projects_files()
    test_redaction()
    test_db_preview_and_confirm()
    print("import tests passed")


if __name__ == "__main__":
    main()
