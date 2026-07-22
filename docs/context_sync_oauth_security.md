# Context Sync OAuth Security

## Controls

- OAuth authorization code flow with PKCE S256.
- Cryptographically random state stored only as a SHA-256 digest.
- State and authorization codes are single use and expire.
- Provider callback and device callback URIs are allowlisted.
- Provider tokens are encrypted at broker rest and erased after grant exchange.
- One-time grants are bound to the device Ed25519 public key.
- The device proves possession by signing the grant ID.
- Grant payloads use ephemeral X25519, HKDF-SHA256, and AES-GCM with the grant ID as associated data.
- Local provider credentials are encrypted before PostgreSQL storage and are cleared on disconnect.
- Tokens are excluded from URLs, frontend JavaScript, audit details, and logs.

## Trust Boundaries

The authorization broker can complete provider OAuth but cannot decrypt the device envelope after delivery. Muslim LLM can retrieve the provider account after grant exchange but never receives the user's provider password, cookies, or copied session token.

Imported content is data, not authority. Imported `system` messages are demoted to user context, wrapped as untrusted, and scanned for prompt-injection patterns. Retrieved content cannot replace Muslim LLM's system policy.

Loopback HTTP callbacks are development-only. Production broker traffic requires HTTPS, strict redirect registration, non-development encryption keys, HSTS, and managed secret rotation.
