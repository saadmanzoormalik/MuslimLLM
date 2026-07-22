# Authentication Architecture

Muslim LLM supports email codes, Apple OIDC, Google OIDC, and a durable guest identity. Every successful method creates the same opaque session boundary.

```text
Browser -> FastAPI auth router -> PostgreSQL identity/session tables
        -> HttpOnly access cookie + rotating refresh cookie
        -> user-scoped chats, projects, settings, and onboarding profile
```

Access and refresh tokens are random opaque values; PostgreSQL stores only HMAC hashes. Access expires in 15 minutes. Refresh lasts 30 days, rotates on use, and revokes all subject sessions if the previous refresh token is replayed.

Social providers use Authorization Code, PKCE, state, nonce, server-side code exchange, JWKS signature validation, issuer validation, and audience validation. An unconfigured provider fails visibly and never produces a mock account.
