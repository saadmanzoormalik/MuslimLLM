# OAuth And Domain Setup

The initial IP deployment is suitable for internal technical testing, guest sessions, and local-model chat. It is not a release-ready OAuth deployment.

Use dedicated names such as `muslimllm.example.com` and `api.muslimllm.example.com`. Configure TLS, streaming/SSE proxy timeouts, upload limits, exact CORS origins, HTTPS callbacks, secure cookies, and HSTS after verification. Do not reuse or modify GrowthPilot's domain configuration.

Google requires a production OAuth client with its exact HTTPS callback registered. Apple requires a Services ID, verified domain, return URL, team ID, key ID, and private key. Add credentials only to `/opt/muslim-llm/.env`, set the matching `AUTH_ALLOW_*` flag, redeploy, and execute the real browser callback flow before marking it configured.

Email remains disabled until a delivery adapter sends single-use codes outside the development mailbox. Guest access remains the truthful fallback.
