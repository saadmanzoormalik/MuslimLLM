# Context Sync Production Deployment

Deploy the public authorization broker independently from the Muslim LLM desktop/backend process.

Required controls:

- HTTPS-only public broker URL and exact provider callback registration.
- Managed PostgreSQL with encrypted backups and least-privilege credentials.
- Random broker encryption key from a managed secret store.
- Strict CORS/redirect allowlists, HSTS, rate limits, structured redacted logs, and alerts.
- Short token/grant TTLs and provider revocation support.
- `AUTH_BROKER_ENVIRONMENT=production` and mock-provider disabled.
- Separate staging and production provider clients and databases.

Reference deployment files are in `deployment/context-auth-broker/` for Docker Compose, Render, Fly.io, Railway, Cloud Run, and an HTTPS reverse proxy. Copy the relevant example, inject secrets through the platform, set `AUTH_BROKER_PUBLIC_URL` to the public HTTPS origin, and register `/v1/oauth/{provider}/callback` with the provider.

The local application must point `AUTH_BROKER_URL` to that HTTPS broker and use a production callback mechanism registered to the installed app. Do not expose the main local FastAPI database or provider retrieval endpoints to the internet.

Before release, run broker security tests, device tests, export fixtures, restart recovery, load tests, existing chat/eval/UI tests, and a clean-device acceptance flow.
