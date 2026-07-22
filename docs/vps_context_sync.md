# VPS Context Sync

Production Context Sync uses durable PostgreSQL jobs and a separate `muslimllm-worker`. The browser may close while progress, checkpoints, errors, deduplication keys, and continuity packages remain stored. Production sets `CONTEXT_SYNC_INLINE_JOBS=false`, so request processes do not own long imports.

The supported ChatGPT path is an official user export ZIP uploaded through the authenticated UI. It does not collect provider passwords, browser cookies, private endpoints, or consumer-history claims. OAuth-style connectors remain unavailable unless their official documented history contracts and credentials are verified.

Operational checks:

```bash
docker compose -p muslimllm --env-file .env -f docker-compose.production.yml ps worker
docker compose -p muslimllm --env-file .env -f docker-compose.production.yml logs --tail 200 worker
```

A release test must import the safe fixture, observe real progressive stages, open the resulting chat with distinct roles and source order, continue it, restart the worker during a second import, and confirm no duplicate records.
