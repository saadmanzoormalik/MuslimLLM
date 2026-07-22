# Cloud Run

Build the repository root with `deployment/context-auth-broker/Dockerfile`, deploy port `8100`, and attach a managed PostgreSQL database through a private connector. Store `AUTH_BROKER_ENCRYPTION_KEY` and provider client secrets in Secret Manager. Set `AUTH_BROKER_ENVIRONMENT=production`, disable localhost callbacks and the mock provider, and map an HTTPS domain before registering provider callbacks.

The health check is `/v1/health`. Do not enable public database access or place provider tokens in Cloud Run environment logs.
