# VPS Release Test

## Infrastructure

- GrowthPilot is healthy before and after, with identical container IDs and volume names.
- Muslim LLM frontend `3200` and backend `8200` respond.
- PostgreSQL, Redis, and Ollama have no host port mappings.
- pgvector exists; migration and seed steps are idempotent.
- Worker and model are healthy; no container restart loop exists.
- `.env` mode is `600`; no secrets occur in images, logs, docs, or source.

## Product

- Onboarding asks only primary use, response preference, and privacy preference.
- Guest sign-in, refresh, sign-out, persistence, chat/project ownership, and conversion tests pass.
- Disabled Google, Apple, and email methods show `Not configured` and reject direct starts.
- Chat emits status, plan, heartbeat, token, sources when used, complete, and visible errors.
- User and assistant messages retain distinct IDs and content after refresh.
- Reasoning labels correspond to actual retrieval, generation, and validation operations.
- Sources, documents, settings, admin, Evals Dashboard, and Context Sync routes load after authentication.
- Islamic values, source discipline, fiqh nuance, social ethics, science neutrality, and refusal tests pass.

## Recovery And Status

Run `deployment/vps/backup-muslim-llm.sh`, `verify-backup-restore.sh`, and a Muslim LLM-only rollback test. Then run the smoke test and confirm GrowthPilot again.

Use `Internal test` until all checks pass. Use `Release candidate` after provider-independent checks and a successful isolated restore. Use `Release ready` only after domain/TLS, configured provider flows, security review, and full release gates pass.
