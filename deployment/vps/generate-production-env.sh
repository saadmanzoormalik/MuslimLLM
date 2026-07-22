#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${MUSLIM_LLM_APP_DIR:-/opt/muslim-llm}"
cd "$APP_DIR"
[[ ! -e .env ]] || { echo ".env already exists; refusing to overwrite it" >&2; exit 1; }

cp .env.production.example .env
db_password="$(openssl rand -hex 32)"
secret_key="$(openssl rand -hex 48)"
auth_secret="$(openssl rand -hex 48)"
encryption_key="$(openssl rand -hex 48)"
context_key="$(openssl rand -hex 48)"

replace() {
  local key="$1" value="$2"
  sed -i "s|^${key}=.*|${key}=${value}|" .env
}

replace POSTGRES_PASSWORD "$db_password"
replace DATABASE_URL "postgresql://muslimllm:${db_password}@db:5432/muslim_llm"
replace SECRET_KEY "$secret_key"
replace AUTH_SECRET_KEY "$auth_secret"
replace ENCRYPTION_KEY "$encryption_key"
replace CONTEXT_SYNC_TOKEN_KEY "$context_key"
chmod 600 .env
unset db_password secret_key auth_secret encryption_key context_key
echo "Created /opt/muslim-llm/.env with independent production secrets"
