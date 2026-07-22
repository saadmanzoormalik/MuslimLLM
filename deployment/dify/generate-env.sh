#!/usr/bin/env bash
set -Eeuo pipefail

RUNTIME_DIR="${DIFY_RUNTIME_DIR:-/opt/muslim-llm/dify-runtime}"
ENV_FILE="$RUNTIME_DIR/.env"

[[ "$RUNTIME_DIR" == "/opt/muslim-llm/dify-runtime" ]] || {
  echo "Unexpected Dify runtime path: $RUNTIME_DIR" >&2
  exit 1
}
[[ -f "$RUNTIME_DIR/.env.example" ]] || {
  echo "Missing official Dify .env.example in $RUNTIME_DIR" >&2
  exit 1
}
[[ ! -e "$ENV_FILE" ]] || {
  echo "$ENV_FILE already exists; refusing to replace secrets" >&2
  exit 1
}

secret() {
  openssl rand -base64 42 | tr -d '\n'
}

cp "$RUNTIME_DIR/.env.example" "$ENV_FILE"
chmod 600 "$ENV_FILE"

set_value() {
  local key="$1" value="$2"
  sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
}

set_value SECRET_KEY "$(secret)"
set_value INIT_PASSWORD "$(secret | cut -c1-30)"
set_value DB_PASSWORD "$(secret)"
redis_password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(42))')"
redis_password_urlencoded="$(python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$redis_password")"
set_value REDIS_PASSWORD "$redis_password"
set_value CELERY_BROKER_URL "redis://:${redis_password_urlencoded}@redis:6379/1"
set_value DIFY_AGENT_REDIS_URL "redis://default:${redis_password_urlencoded}@redis:6379/0"
weaviate_key="$(secret)"
set_value WEAVIATE_API_KEY "$weaviate_key"
set_value WEAVIATE_AUTHENTICATION_APIKEY_ALLOWED_KEYS "$weaviate_key"
sandbox_api_key="$(secret)"
set_value SANDBOX_API_KEY "$sandbox_api_key"
set_value CODE_EXECUTION_API_KEY "$sandbox_api_key"
set_value PLUGIN_DAEMON_KEY "$(secret)"
set_value PLUGIN_DIFY_INNER_API_KEY "$(secret)"
set_value DIFY_AGENT_SERVER_SECRET_KEY "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
set_value DIFY_AGENT_SHELLCTL_AUTH_TOKEN "$(secret)"
set_value CHECK_UPDATE_URL ""
set_value ENABLE_COLLABORATION_MODE "false"
set_value COMPOSE_PROFILES "postgresql,weaviate"
set_value EXPOSE_NGINX_PORT "3300"
set_value EXPOSE_NGINX_SSL_PORT "3443"
set_value EXPOSE_PLUGIN_DEBUGGING_HOST "127.0.0.1"
set_value EXPOSE_PLUGIN_DEBUGGING_PORT "3503"
set_value WEAVIATE_DISABLE_TELEMETRY "true"
set_value SSRF_PROXY_ALLOW_PRIVATE_DOMAINS "muslimllm-ollama"
set_value SSRF_PROXY_ALLOW_PRIVATE_IPS "false"
set_value FORCE_VERIFYING_SIGNATURE "true"

echo "Created $ENV_FILE with mode 600"
