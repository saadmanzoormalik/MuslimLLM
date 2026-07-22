import os
import unittest
from datetime import UTC, datetime, timedelta

import httpx
import psycopg

from app.context_sync.device_identity import load_device_identity
from work.context_sync_live_support import BROKER, PROVIDER, create_ready_grant, services_ready


@unittest.skipUnless(services_ready(), "Context Sync services are not running")
class ContextAuthBrokerTests(unittest.TestCase):
    def test_invalid_state_and_missing_pkce_are_rejected(self):
        invalid = httpx.get(f"{BROKER}/v1/oauth/demo/callback?code=invalid&state=invalid", timeout=5)
        self.assertEqual(400, invalid.status_code)
        missing = httpx.post(f"{PROVIDER}/oauth/token", data={"code": "invalid"}, timeout=5)
        self.assertEqual(400, missing.status_code)

    def test_unapproved_redirect_is_rejected(self):
        identity = load_device_identity().public_bundle()
        response = httpx.post(
            f"{BROKER}/v1/connections/demo/start",
            json={
                "device_callback_uri": "https://attacker.example/callback",
                "device_signing_public_key": identity["signing_public_key"],
                "device_encryption_public_key": identity["encryption_public_key"],
                "device_state": "state-with-at-least-twenty-four-characters",
                "platform": "test",
                "app_version": "test",
                "requested_capability": "context_sync",
            },
            timeout=5,
        )
        self.assertEqual(400, response.status_code)

    def test_wrong_device_replay_and_expired_grants_are_rejected(self):
        flow = create_ready_grant()
        identity = load_device_identity()
        # A different public key is rejected before signature verification.
        from app.context_sync.device_identity import _new_identity
        other = _new_identity()
        rejected = httpx.post(
            f"{BROKER}/v1/grants/{flow['grant_id']}/exchange",
            json={"device_signing_public_key": other.public_bundle()["signing_public_key"], "signature": other.sign_grant(flow["grant_id"])},
            timeout=5,
        )
        self.assertEqual(403, rejected.status_code)

        accepted = httpx.post(
            f"{BROKER}/v1/grants/{flow['grant_id']}/exchange",
            json={"device_signing_public_key": identity.public_bundle()["signing_public_key"], "signature": identity.sign_grant(flow["grant_id"])},
            timeout=5,
        )
        self.assertEqual(200, accepted.status_code)
        self.assertNotIn("access_token", str(accepted.request.url))
        replay = httpx.post(
            f"{BROKER}/v1/grants/{flow['grant_id']}/exchange",
            json={"device_signing_public_key": identity.public_bundle()["signing_public_key"], "signature": identity.sign_grant(flow["grant_id"])},
            timeout=5,
        )
        self.assertEqual(409, replay.status_code)

        expired = create_ready_grant()
        database_url = os.getenv("AUTH_BROKER_DATABASE_URL", "postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm")
        with psycopg.connect(database_url) as conn:
            conn.execute("update auth_broker_grants set expires_at=%s where id=%s", (datetime.now(UTC) - timedelta(seconds=1), expired["grant_id"]))
        expired_response = httpx.post(
            f"{BROKER}/v1/grants/{expired['grant_id']}/exchange",
            json={"device_signing_public_key": identity.public_bundle()["signing_public_key"], "signature": identity.sign_grant(expired["grant_id"])},
            timeout=5,
        )
        self.assertEqual(410, expired_response.status_code)


if __name__ == "__main__":
    unittest.main()
