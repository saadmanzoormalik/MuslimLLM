import base64
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


KEYCHAIN_SERVICE = "com.muslimllm.context-sync.device"
KEYCHAIN_ACCOUNT = "default"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class DeviceIdentity:
    installation_id: str
    signing_private_key: str
    encryption_private_key: str

    @property
    def signing_key(self) -> Ed25519PrivateKey:
        return Ed25519PrivateKey.from_private_bytes(_unb64(self.signing_private_key))

    @property
    def encryption_key(self) -> X25519PrivateKey:
        return X25519PrivateKey.from_private_bytes(_unb64(self.encryption_private_key))

    def public_bundle(self) -> dict[str, str]:
        signing = self.signing_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        encryption = self.encryption_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return {"installation_id": self.installation_id, "signing_public_key": _b64(signing), "encryption_public_key": _b64(encryption)}

    def sign_grant(self, grant_id: str) -> str:
        return _b64(self.signing_key.sign(grant_id.encode()))

    def decrypt_grant(self, envelope: dict, grant_id: str) -> dict:
        if envelope.get("alg") != "x25519-aesgcm-v1":
            raise ValueError("Unsupported grant encryption")
        ephemeral = X25519PublicKey.from_public_bytes(_unb64(envelope["ephemeral_public_key"]))
        shared = self.encryption_key.exchange(ephemeral)
        key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"muslim-llm-context-grant-v1").derive(shared)
        raw = AESGCM(key).decrypt(_unb64(envelope["nonce"]), _unb64(envelope["ciphertext"]), grant_id.encode())
        return json.loads(raw.decode())


def _new_identity() -> DeviceIdentity:
    signing = Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    encryption = X25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
    return DeviceIdentity(str(uuid4()), _b64(signing), _b64(encryption))


def _keychain_read() -> str | None:
    if platform.system() != "Darwin" or os.getenv("CONTEXT_SYNC_USE_KEYCHAIN", "true").lower() != "true":
        return None
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _keychain_write(payload: str) -> bool:
    if platform.system() != "Darwin" or os.getenv("CONTEXT_SYNC_USE_KEYCHAIN", "true").lower() != "true":
        return False
    result = subprocess.run(
        ["security", "add-generic-password", "-U", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w", payload],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def load_device_identity() -> DeviceIdentity:
    from_env = os.getenv("CONTEXT_SYNC_DEVICE_IDENTITY_JSON")
    payload = from_env or _keychain_read()
    if payload:
        return DeviceIdentity(**json.loads(payload))

    path = Path(os.getenv("CONTEXT_SYNC_DEVICE_IDENTITY_FILE", str(Path.home() / ".muslim-llm" / "device-identity.json")))
    if path.exists():
        return DeviceIdentity(**json.loads(path.read_text(encoding="utf-8")))

    identity = _new_identity()
    serialized = json.dumps(identity.__dict__, separators=(",", ":"))
    if not _keychain_write(serialized):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
        path.chmod(0o600)
    return identity
