# Context Sync Lab

Context Sync Lab is the isolated development surface at `/context-sync-lab`. It is disabled unless both the backend and frontend are started with the lab flags.

```bash
./deployment/context-sync-macos/start-lab.sh
```

The lab uses the PostgreSQL schema `context_sync_lab` and the controlled local storage path configured by `CONTEXT_SYNC_LAB_STORAGE_PATH`. Imported records do not appear in normal chats, projects, or the consumer sidebar. Only **Promote to Muslim LLM** writes validated records to production tables.

The four areas are provider connection, durable sync state, read-only workspace preview, and release validation. Closing the browser does not stop a job. Jobs in `queued`, `importing`, or `validating` are recovered when FastAPI restarts.

Use **Delete lab data** through `DELETE /context-sync-lab/data` to remove lab database records and locally retained export ZIPs.

## Real-account manual check

1. Open `/context-sync-lab` and choose OpenAI / ChatGPT.
2. Open the official export guide and request a ChatGPT data export.
3. Select the downloaded ZIP with the macOS picker; import starts immediately.
4. Close and reopen the browser. Confirm the durable job and preview remain available.
5. Restart FastAPI during a queued import. Confirm the stored archive and checkpoints resume.
6. Inspect chats, alternate branches, files, projects, exceptions, and continuity packages.
7. Run **Test continuation** and verify the source references and sandbox flags.
8. Review every release gate, then choose **Promote to Muslim LLM**.
9. Repeat promotion and confirm no duplicate chats or projects are created.
10. Confirm pre-existing Muslim LLM chats and projects are unchanged.

Future approved provider history connectors implement the same provider/import boundary and produce the normalized lab records used by preview and promotion. They must remain disabled until official scopes and contract tests exist.
