# Private Dify Runtime

This directory hardens the official Dify 1.16 Docker runtime for the Muslim Knowledge Fabric.

- Compose project: `muslim-knowledge-fabric`
- Runtime: `/opt/muslim-llm/dify-runtime`
- Console: `127.0.0.1:3300` only
- Shared network: `muslimllm-fabric`
- Local inference: `http://muslimllm-ollama:11434`
- Stable knowledge store: isolated Dify Postgres and Weaviate volumes
- GrowthPilot: no shared files, ports, networks, secrets, or volumes

Use `manage.sh` for lifecycle commands. Generate `.env` once with `generate-env.sh`; it refuses to overwrite an existing secret file. Keep the Dify console private and access it only through an SSH tunnel.

## Agentic Network

`connect-network.py` binds the main Chatflow to the published specialist workflow tools and the seven stable knowledge bases. It excludes `LIVE_RESEARCH_CANDIDATES` from serving, synchronizes version-controlled specialist graphs, and resyncs Dify's version-pinned workflow-tool providers.

```bash
python3 deployment/dify/bootstrap.py
python3 deployment/dify/connect-network.py
python3 deployment/dify/connect-network.py --publish
```

The publish command provisions the main app's private service credential in `/opt/muslim-llm/dify-runtime/.fabric-api-credentials.json` with mode `600`. Do not expose or commit that file.
