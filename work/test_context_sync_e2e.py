import json
import os
import unittest

import httpx
import psycopg

from work.context_sync_live_support import BACKEND, complete_demo_flow, services_ready, wait_for_job


@unittest.skipUnless(services_ready(), "Context Sync services are not running")
class ContextSyncEndToEndTests(unittest.TestCase):
    def test_authorize_import_continue_dedupe_and_disconnect(self):
        database_url = os.getenv("DATABASE_URL", "postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm")
        with psycopg.connect(database_url) as conn:
            workspace_guest_id = conn.execute(
                """select guest_id from chats where guest_id is not null and imported_from_provider is null
                   group by guest_id order by count(*) desc limit 1"""
            ).fetchone()[0]
        httpx.delete(f"{BACKEND}/context-sync/imported-data/demo", timeout=15).raise_for_status()
        client = httpx.Client(base_url=BACKEND, timeout=120)
        client.post("/auth/guest", json={"claim_existing_workspace": False}).raise_for_status()
        first = complete_demo_flow()
        first_status = wait_for_job(first["job_id"])
        self.assertEqual("completed", first_status["status"])
        self.assertTrue(first_status["ready_for_use"])

        validation = httpx.get(f"{BACKEND}/context-sync/validation/{first['job_id']}", timeout=5).json()
        self.assertEqual(20, validation["conversations_retrieved"])
        self.assertEqual(41, validation["messages_retrieved"])
        self.assertEqual(3, validation["projects_retrieved"])
        self.assertEqual(5, validation["files_retrieved"])

        # Claim only the newly imported, previously unowned demo rows into this isolated test guest.
        with psycopg.connect(database_url) as conn:
            guest_id = conn.execute("select guest_id from auth_sessions where session_token_hash is not null and guest_id is not null order by created_at desc limit 1").fetchone()[0]
            conn.execute("update projects set guest_id=%s where imported_from_provider='demo' and user_id is null and guest_id is null", (guest_id,))
            conn.execute("update chats set guest_id=%s where imported_from_provider='demo' and user_id is null and guest_id is null", (guest_id,))
        chats = [row for row in client.get("/chats").json() if row.get("imported_from_provider") == "demo"]
        projects = [row for row in client.get("/projects").json() if row.get("imported_from_provider") == "demo"]
        self.assertEqual(20, len(chats))
        self.assertEqual(3, len(projects))

        chat_id = first_status["entry_chat_id"]
        imported = client.get(f"/chats/{chat_id}").json()
        self.assertGreaterEqual(len(imported["messages"]), 2)
        continuation = client.post(
            "/chat",
            json={"chat_id": chat_id, "message": "Continue this discussion. What concrete next action follows from the people, trust, evidence, and dignity we identified?", "stream": True},
            timeout=120,
        )
        continuation.raise_for_status()
        self.assertIn("event: complete", continuation.text)
        self.assertGreater(len(continuation.text), 100)

        second = complete_demo_flow()
        second_status = wait_for_job(second["job_id"])
        self.assertEqual("completed", second_status["status"])
        second_validation = httpx.get(f"{BACKEND}/context-sync/validation/{second['job_id']}", timeout=5).json()
        self.assertEqual(20, second_validation["duplicates_prevented"])
        chats_after = [row for row in client.get("/chats").json() if row.get("imported_from_provider") == "demo"]
        self.assertEqual(20, len(chats_after))

        for flow in (first, second):
            response = httpx.post(f"{BACKEND}/context-sync/disconnect/{flow['connection_id']}", timeout=10)
            response.raise_for_status()
        with psycopg.connect(database_url) as conn:
            rows = conn.execute("select status,encrypted_token_json from provider_connections where id in (%s,%s)", (first["connection_id"], second["connection_id"])).fetchall()
            conn.execute("update projects set guest_id=%s where imported_from_provider='demo'", (workspace_guest_id,))
            conn.execute("update chats set guest_id=%s where imported_from_provider='demo'", (workspace_guest_id,))
        self.assertTrue(all(status == "disconnected" and token == {} for status, token in rows))
        client.request("DELETE", "/account", json={"confirmation": "DELETE"})
        client.close()


if __name__ == "__main__":
    unittest.main()
