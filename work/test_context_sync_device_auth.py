import base64
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.context_sync.device_identity import _new_identity, load_device_identity


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class ContextSyncDeviceAuthTests(unittest.TestCase):
    def test_device_can_decrypt_only_its_bound_grant(self):
        identity = _new_identity()
        recipient_raw = unb64(identity.public_bundle()["encryption_public_key"])
        ephemeral = X25519PrivateKey.generate()
        shared = ephemeral.exchange(X25519PublicKey.from_public_bytes(recipient_raw))
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"muslim-llm-context-grant-v1").derive(shared)
        grant_id = "grant-123"
        nonce = os.urandom(12)
        payload = {"access_token": "secret", "provider": "demo"}
        ciphertext = AESGCM(key).encrypt(nonce, json.dumps(payload).encode(), grant_id.encode())
        envelope = {
            "alg": "x25519-aesgcm-v1",
            "ephemeral_public_key": b64(ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)),
            "nonce": b64(nonce),
            "ciphertext": b64(ciphertext),
        }
        self.assertEqual(payload, identity.decrypt_grant(envelope, grant_id))
        with self.assertRaises(Exception):
            _new_identity().decrypt_grant(envelope, grant_id)

    def test_fallback_identity_file_has_owner_only_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity.json"
            with patch.dict(os.environ, {"CONTEXT_SYNC_USE_KEYCHAIN": "false", "CONTEXT_SYNC_DEVICE_IDENTITY_FILE": str(path)}, clear=False):
                first = load_device_identity()
                second = load_device_identity()
            self.assertEqual(first.installation_id, second.installation_id)
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))


if __name__ == "__main__":
    unittest.main()
