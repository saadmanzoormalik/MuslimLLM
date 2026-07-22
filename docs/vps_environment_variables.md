# VPS Environment Variables

Start from `.env.production.example`; generate independent values with `deployment/vps/generate-production-env.sh`.

Required secrets: `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY`, `AUTH_SECRET_KEY`, `ENCRYPTION_KEY`, and `CONTEXT_SYNC_TOKEN_KEY`. The generator uses separate random values and sets `.env` mode `600`.

Required public configuration: `PUBLIC_FRONTEND_URL`, `PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_API_BASE_URL`, `AUTH_ALLOWED_ORIGINS`, and `AUTH_ALLOWED_REDIRECT_URIS`.

Initial provider state:

| Capability | State | Requirement to enable |
|---|---|---|
| Guest access | Enabled | None |
| Local LLM | Enabled | Private Ollama service and installed `muslim-llm-local` model |
| Deterministic embeddings | Enabled | None |
| Google sign-in | Disabled | HTTPS domain, client ID, secret, and approved callback |
| Apple sign-in | Disabled | HTTPS domain, Services ID, team/key IDs, private key, and callback |
| Email code | Disabled | A real delivery adapter; the current local mailbox is development-only |
| External LLM | Disabled | Explicit approval plus endpoint/key/model |
| Remote updates | Disabled | Signed update service and verification key |

Never add placeholder provider credentials or mark a disabled provider as configured.
