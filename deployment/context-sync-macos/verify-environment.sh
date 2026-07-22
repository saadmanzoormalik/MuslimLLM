#!/bin/zsh
set -euo pipefail
check_url() {
  if curl -fsS "$2" >/dev/null 2>&1; then printf "%-26s OK\n" "$1"; else printf "%-26s NOT READY\n" "$1"; return 1; fi
}
printf "%-26s %s\n" "PostgreSQL" "$(pg_isready -h 127.0.0.1 -p "${MUSLIM_LLM_POSTGRES_PORT:-5433}" >/dev/null 2>&1 && echo OK || echo NOT\ READY)"
check_url "Demo AI Account" http://127.0.0.1:8200/health
check_url "Authorization Broker" http://127.0.0.1:8100/v1/health
check_url "Muslim LLM backend" http://127.0.0.1:8000/health
check_url "Muslim LLM frontend" http://127.0.0.1:3000/
check_url "Ollama" http://127.0.0.1:11434/api/tags
if security -h >/dev/null 2>&1; then printf "%-26s OK\n" "macOS Keychain"; else printf "%-26s NOT READY\n" "macOS Keychain"; fi
if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null && lsof -nP -iTCP:8100 -sTCP:LISTEN >/dev/null && lsof -nP -iTCP:8200 -sTCP:LISTEN >/dev/null; then printf "%-26s OK\n" "Callback ports"; fi
printf "%-26s OK (loopback HTTP)\n" "Development transport"
