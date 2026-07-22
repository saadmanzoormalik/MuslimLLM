# Authentication Security Model

- Passwordless by default; no raw passwords are stored.
- Email codes, access tokens, refresh tokens, guest secrets, IP addresses, state, and nonce are hashed where equality lookup is needed.
- PKCE verifier and nonce are encrypted only for the short OAuth transaction.
- Web sessions use HttpOnly, SameSite=Lax cookies; production enables Secure.
- Refresh tokens rotate and previous-token replay revokes the subject's sessions.
- Unsafe cross-origin requests are rejected; production CORS uses explicit origins.
- Provider signatures, issuer, audience, nonce, expiry, state, and callback are validated.
- Security headers deny framing, sniffing, sensitive browser permissions, and unsafe referrer leakage.
- Audit records contain categories and hashes, never credentials or raw tokens.
