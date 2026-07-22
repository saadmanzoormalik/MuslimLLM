# VPS Security

The production stack publishes only frontend port `3200` and backend port `8200`. PostgreSQL `5432`, Redis `6379`, and Ollama `11434` are exposed only inside `muslimllm-network`. Dedicated volumes use the `muslimllm-` prefix.

Controls include non-root frontend/backend/worker processes, dropped Linux capabilities, `no-new-privileges`, strict origin allowlists, authenticated data/eval/import routes, hashed sessions and codes, rotating refresh tokens, archive size and extraction controls, executable rejection, SSRF controls, security headers, container memory/CPU limits, healthchecks, restart policies, and bounded Docker logs.

Keep `/opt/muslim-llm/.env` mode `600`. Never print or commit it. Audit output must not contain prompts, imported content, email codes, OAuth tokens, session tokens, passwords, or private keys.

The IP-only verification deployment uses `AUTH_SECURE_COOKIES=false`. Before public release, add a dedicated domain, TLS, HTTP-to-HTTPS redirects, HSTS after validation, `AUTH_SECURE_COOKIES=true`, and exact HTTPS origins. Do not change GrowthPilot's proxy or domain configuration.
