# VPS Rollback

Deployments tag frontend and backend images with a timestamp and record the previous version under `deployment/state`. A failed deployment attempts an app-only rollback while preserving PostgreSQL, imports, documents, updates, Redis, and model volumes.

```bash
cd /opt/muslim-llm
./deployment/vps/rollback-muslim-llm.sh
./deployment/vps/rollback-muslim-llm.sh 2026.07.15-120000
```

After rollback, run status, the smoke test, and GrowthPilot health checks. Never use global prune, global container stops, volume deletion, or `docker compose down -v`. Rollback must use the `muslimllm` Compose project only.
