# Context Sync MacBook Demo

## Configure

From the repository root:

```bash
export DATABASE_URL="postgresql://saadmanzoor@127.0.0.1:5433/muslim_llm"
export CONTEXT_SYNC_TOKEN_KEY="replace-with-a-stable-local-secret"
export CONTEXT_SYNC_ALLOW_MOCK_PROVIDER=true
export APP_ENVIRONMENT=development
```

## Start

```bash
chmod +x deployment/context-sync-macos/*.sh
./deployment/context-sync-macos/start-all.sh
```

Open [Muslim LLM](http://127.0.0.1:3000) or [Transfer Context](http://127.0.0.1:3000/context-sync).

## Demo AI Account

1. Select **Demo AI Account**.
2. Choose **Continue to Demo AI Account**.
3. On the provider page, choose **Continue as Demo User**.
4. Watch the progress screen, then open the imported conversation.
5. Ask a follow-up that depends on the prior conversation.

The seeded account imports 20 chats, 3 projects, 5 file references, branches, attachments, and timestamps.

## Official Export

Select ChatGPT, Claude, Gemini, or another tile marked for secure import. Choose **Continue secure connection**, then select the original provider ZIP or supported JSON/CSV/TXT/Markdown export. The importer detects `conversations.json` in ZIP archives and starts the durable job immediately.

For a fixture test:

```bash
curl -F "file=@work/fixtures/imports/chatgpt_export_sample.json" \
  http://127.0.0.1:8000/context-sync/official-export/chatgpt
```

## Inspect And Reset

```bash
curl http://127.0.0.1:8000/context-sync/status
curl http://127.0.0.1:8000/context-sync/connections
curl http://127.0.0.1:8000/projects
curl -X DELETE http://127.0.0.1:8000/context-sync/imported-data/demo
curl -X POST http://127.0.0.1:8000/context-sync/connections/demo/disconnect
./deployment/context-sync-macos/verify-environment.sh
./deployment/context-sync-macos/stop-all.sh
```

## Callback Troubleshooting

- Confirm ports 3000, 8000, 8100, and 8200 report `OK` in `verify-environment.sh`.
- Use `127.0.0.1` consistently; callback allowlists intentionally reject unrelated hosts and paths.
- Restart all services after changing callback or broker environment variables.
- Check `.context-sync-run/backend.log`, `auth-broker.log`, and `mock-provider.log`.
- An expired or reused flow is intentionally rejected; return to Transfer Context and begin again.
