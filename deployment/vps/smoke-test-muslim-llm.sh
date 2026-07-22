#!/usr/bin/env bash
set -Eeuo pipefail

FRONTEND_URL="${PUBLIC_FRONTEND_URL:-http://127.0.0.1:3200}"
BACKEND_URL="${PUBLIC_BACKEND_URL:-http://127.0.0.1:8200}"
cookie_jar="$(mktemp)"
stream_file="$(mktemp)"
trap 'rm -f "$cookie_jar" "$stream_file"' EXIT

curl_retry=(--retry 5 --retry-delay 2 --retry-all-errors)

curl -fsSI "${curl_retry[@]}" --max-time 20 "$FRONTEND_URL" >/dev/null
curl -fsS "${curl_retry[@]}" --max-time 20 "$BACKEND_URL/health" | grep -q '"ok":true'
curl -fsS "${curl_retry[@]}" --max-time 20 "$BACKEND_URL/auth/providers" | grep -q '"guest"'
curl -fsS "${curl_retry[@]}" --max-time 20 -c "$cookie_jar" -b "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -d '{"claim_existing_workspace":false}' \
  "$BACKEND_URL/auth/guest" | grep -q '"account_type":"guest"'
curl -fsS "${curl_retry[@]}" --max-time 180 -N -c "$cookie_jar" -b "$cookie_jar" \
  -H 'Content-Type: application/json' \
  -d '{"message":"In two sentences, explain why honesty matters in business.","model":"muslim-llm-core","stream":true}' \
  "$BACKEND_URL/chat" > "$stream_file"
grep -q '"token"' "$stream_file"
grep -q '^event: complete' "$stream_file"
grep -q '"user_message"' "$stream_file"
curl -fsS "${curl_retry[@]}" --max-time 20 -b "$cookie_jar" "$BACKEND_URL/chats" | grep -q '\['
echo "Muslim LLM smoke tests passed"
