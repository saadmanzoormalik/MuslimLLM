# Muslim LLM VPS Deployment

## Fixed deployment boundary

- SSH: `ssh -i ~/.ssh/codex_growthpilot_vps -o IdentitiesOnly=yes ubuntu@148.113.203.232`
- App directory: `/opt/muslim-llm`
- Compose project: `muslimllm`
- Frontend: `http://148.113.203.232:3200`
- Backend: `http://148.113.203.232:8200`
- Health: `http://148.113.203.232:8200/health`

Never edit, rebuild, restart, or reuse anything under `/opt/growthpilot`. Never bind Muslim LLM to ports `3000`, `8000`, or `8100`. Never reuse GrowthPilot volumes, networks, secrets, PostgreSQL, or Redis.

## Deploy

Upload the source without `.env`, `.git`, `node_modules`, `.next`, local databases, logs, or caches. On the VPS:

```bash
sudo mkdir -p /opt/muslim-llm
sudo chown -R ubuntu:ubuntu /opt/muslim-llm
cd /opt/muslim-llm
./deployment/vps/deploy-muslim-llm.sh
```

The deploy script verifies GrowthPilot, host ports, RAM, CPU, disk, Docker, secrets, image builds, migrations, health, guest authentication, streaming chat, persistence, and GrowthPilot again. It stops before changing the server if a release gate fails.

```bash
./deployment/vps/status-muslim-llm.sh
./deployment/vps/logs-muslim-llm.sh
./deployment/vps/restart-muslim-llm.sh
./deployment/vps/stop-muslim-llm.sh
```

Only commands using `docker compose -p muslimllm -f docker-compose.production.yml` may manage this app.
