import os
import time
from pathlib import Path

from joserfc import jwk, jwt


def apple_client_secret() -> str:
    path = os.getenv("APPLE_PRIVATE_KEY_PATH", "")
    if not path or not Path(path).exists():
        return ""
    key = jwk.ECKey.import_key(Path(path).read_bytes())
    now = int(time.time())
    return jwt.encode(
        {"alg": "ES256", "kid": os.getenv("APPLE_KEY_ID", "")},
        {"iss": os.getenv("APPLE_TEAM_ID", ""), "iat": now, "exp": now + 300,
         "aud": "https://appleid.apple.com", "sub": os.getenv("APPLE_CLIENT_ID", "")},
        key, algorithms=["ES256"],
    )
