import json
import tempfile
import time
import zipfile
from pathlib import Path

import httpx

from app.db import get_conn
from work.test_openai_export_parser import branched_conversation

API_BASE = "http://127.0.0.1:8000"


def run():
    session_id = None
    consent_id = None
    job_id = None
    connection_id = None
    upload_token = None
    try:
        with httpx.Client(timeout=30) as client:
            denied = client.post(f"{API_BASE}/context-sync/openai/agree-and-connect", json={"accepted": False, "device_id": "api-contract"})
            assert denied.status_code == 400
            agreed = client.post(f"{API_BASE}/context-sync/openai/agree-and-connect", json={"accepted": True, "device_id": "api-contract"})
            agreed.raise_for_status()
            session_id = agreed.json()["session_id"]
            assert agreed.json()["next_action"] == "open_official_export"
            assert agreed.json()["action_url"].startswith("https://help.openai.com/")

            with tempfile.TemporaryDirectory() as directory:
                archive_path = Path(directory) / "chatgpt-export.zip"
                conversation = branched_conversation(f"transfer-api-{session_id}")
                with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("conversations.json", json.dumps([conversation]))
                with archive_path.open("rb") as handle:
                    uploaded = client.post(
                        f"{API_BASE}/context-sync/openai/session/{session_id}/select-export",
                        files={"file": (archive_path.name, handle, "application/zip")},
                    )
                uploaded.raise_for_status()
                job_id = uploaded.json()["job_id"]

            deadline = time.monotonic() + 20
            current = {}
            while time.monotonic() < deadline:
                current = client.get(f"{API_BASE}/context-sync/openai/session/{session_id}").json()
                if current["state"] in {"completed", "completed_with_exceptions"}:
                    break
                time.sleep(0.2)
            assert current["state"] in {"completed", "completed_with_exceptions"}
            assert current["ready_for_use"] is True
            assert current["chats_restored"] == 1
            assert current["latest_chat_id"]
            answer_parts = []
            with client.stream(
                "POST",
                f"{API_BASE}/chat",
                json={
                    "chat_id": current["latest_chat_id"],
                    "message": "In the imported conversation, which option was active? Answer in one sentence.",
                    "model": "muslim-llm-core",
                    "stream": True,
                },
                timeout=120,
            ) as streamed:
                streamed.raise_for_status()
                for line in streamed.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = json.loads(line.removeprefix("data: "))
                    if payload.get("token"):
                        answer_parts.append(payload["token"])
            answer = "".join(answer_parts).strip().lower()
            assert answer
            assert "active option" in answer, answer
            report = client.get(f"{API_BASE}/context-sync/openai/session/{session_id}/report")
            report.raise_for_status()
            assert report.json()["report"]["branches_preserved"] >= 1
    finally:
        if session_id:
            with get_conn() as conn:
                session = conn.execute("select consent_id,sync_job_id from context_transfer_sessions where id=%s", (session_id,)).fetchone()
                if session:
                    consent_id = str(session["consent_id"])
                    job_id = str(session["sync_job_id"]) if session["sync_job_id"] else job_id
                if job_id:
                    job = conn.execute("select connection_id,inventory_json from sync_jobs where id=%s", (job_id,)).fetchone()
                    if job:
                        connection_id = str(job["connection_id"]) if job["connection_id"] else None
                        upload_token = (job["inventory_json"] or {}).get("upload_token")
                    conn.execute("delete from chats where import_job_id=%s", (job_id,))
                    conn.execute("delete from projects where import_job_id=%s", (job_id,))
                conn.execute("delete from context_transfer_sessions where id=%s", (session_id,))
                if job_id:
                    conn.execute("delete from sync_jobs where id=%s", (job_id,))
                if upload_token:
                    conn.execute("delete from context_sync_uploads where id=%s", (upload_token,))
                if connection_id:
                    conn.execute("delete from provider_connections where id=%s", (connection_id,))
                if consent_id:
                    conn.execute("delete from context_transfer_consents where id=%s", (consent_id,))


if __name__ == "__main__":
    run()
    print("OpenAI transfer API checks passed")
