# MacBook Context Sync Demo

Run `./deployment/context-sync-macos/start-all.sh`, open the printed Transfer Context URL, choose **Demo AI Account**, and approve the development account. Use `./deployment/context-sync-macos/stop-all.sh` to stop processes started by these scripts. Exact environment, export, status, reset, and callback commands are in `docs/context_sync_macbook_demo.md`.

The device identity is stored in macOS Keychain under `com.muslimllm.context-sync.device`. If Keychain is unavailable, development falls back to a mode-600 file under `~/.muslim-llm`.
