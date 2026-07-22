import unittest

from app.context_sync.service import ensure_context_sync_ready
from app.context_sync.state_machine import create_transfer_consent, create_transfer_session, get_transfer_session, refresh_transfer_session, transition_session
from app.db import get_conn


class OpenAISyncResumeTests(unittest.TestCase):
    def setUp(self):
        ensure_context_sync_ready()
        self.consent = create_transfer_consent("resume-device", accepted=True)
        self.session = create_transfer_session(str(self.consent["id"]), "resume-device")
        with get_conn() as conn:
            job = conn.execute(
                """
                insert into sync_jobs (provider_id,status,stage,ready_for_use,percent,display_message)
                values ('chatgpt','running','creating_chats',true,55,'Restoring conversations') returning id
                """
            ).fetchone()
        self.job_id = str(job["id"])
        self.session_id = str(self.session["id"])
        transition_session(self.session_id, "importing_recent_context", sync_job_id=self.job_id, background_sync_continues=True)

    def tearDown(self):
        with get_conn() as conn:
            conn.execute("delete from context_transfer_sessions where id=%s", (self.session_id,))
            conn.execute("delete from sync_jobs where id=%s", (self.job_id,))
            conn.execute("delete from context_transfer_consents where id=%s", (self.consent["id"],))

    def test_state_survives_process_reconstruction_and_reaches_completion(self):
        restored = get_transfer_session(self.session_id)
        self.assertEqual("importing_recent_context", restored["state"])
        self.assertTrue(restored["ready_for_use"])
        self.assertTrue(restored["background_sync_continues"])
        with get_conn() as conn:
            conn.execute("update sync_jobs set status='completed',stage='completed',percent=100,ready_for_use=true where id=%s", (self.job_id,))
        completed = refresh_transfer_session(self.session_id)
        self.assertEqual("completed", completed["state"])
        self.assertEqual(100, completed["progress_percent"])


if __name__ == "__main__":
    unittest.main()
