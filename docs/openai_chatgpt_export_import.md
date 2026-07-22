# OpenAI Context Sync

Muslim LLM imports ChatGPT consumer history through the official ChatGPT data export. OpenAI API credentials are tested separately and never imply access to ChatGPT chats, projects, or files.

## User Flow

1. Open `http://127.0.0.1:3000/`.
2. Select **LLM Context Sync**.
3. Select **Connect OpenAI**.
4. Request or select the official ChatGPT export ZIP.
5. Optionally authorize one folder with **Watch Downloads for export**.
6. Leave or close the page if needed. Folder detection and the PostgreSQL-backed job continue.

Imported chats remain in **All chats**. Confirmed or confidently reconstructed project titles appear under **Projects**. Existing local data is unchanged.

## Local Launch

```bash
./deployment/context-sync-macos/start-openai-sync.sh
```

The default model and continuity processing remain local through Ollama. The export parser reads the selected archive locally, preserves conversation trees and branch provenance, quarantines suspicious files, and never elevates imported content into system authority.

## Implementation Prompt Amendment

After the user selects **Connect OpenAI**, resolve the best officially supported method. If verified consumer-history authorization exists, use it. Otherwise open OpenAI's official export surface and keep Muslim LLM ready to receive the export.

The user completes account authentication and export approval only on OpenAI's official surface. Muslim LLM must never collect OpenAI passwords, cookies, session tokens, or use private ChatGPT endpoints. API credentials remain separate from ChatGPT history.

After one explicit local permission action, the backend owns the rest of the pipeline:

```text
Native folder authorization
-> persistent approved-folder watch
-> local ZIP detection
-> security validation
-> durable PostgreSQL import job
-> recent chats ready
-> projects, files, and continuity restored
-> completion report
```

The watcher may inspect only direct ZIP children of the selected folder. The API exposes only the folder name, never its full path. Authorization survives browser closure and backend restarts, can be revoked from the sync screen, and never grants access to unrelated folders.

## Verification

```bash
PYTHONPATH=backend backend/.venv/bin/python -m unittest \
  work/test_openai_context_sync.py \
  work/test_openai_export_parser.py \
  work/test_openai_context_sync_security.py \
  work/test_openai_context_sync_resume.py \
  work/test_openai_context_continuity.py
```

The full synthetic parser profile is:

```bash
PYTHONPATH=backend backend/.venv/bin/python work/load_test_openai_context_sync.py --full
```
