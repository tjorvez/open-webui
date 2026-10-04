#!/usr/bin/env bash
set -euo pipefail
image="${1:?Usage: smoke-test.sh IMAGE}"
container="open-webui-smoke-${RANDOM}"
cleanup() {
  result=$?
  if [[ "$result" -ne 0 ]]; then
    docker logs --tail=100 "$container" >&2 || true
  fi
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "$container" --read-only --network none \
  --tmpfs /tmp:rw,size=512m --tmpfs /app/backend/data:rw,size=512m \
  -e HOME=/tmp/open-webui/home -e STATIC_DIR=/tmp/open-webui/static \
  -e PYTHONDONTWRITEBYTECODE=1 -e HF_HUB_OFFLINE=1 \
  -e WEBUI_SECRET_KEY=smoke-test-only-secret-key-at-least-32-characters \
  -e WEBUI_ADMIN_EMAIL=admin@example.invalid \
  -e WEBUI_ADMIN_PASSWORD=smoke-test-only-password \
  -e ENABLE_SIGNUP=false -e ENABLE_OLLAMA_API=false \
  -e ENABLE_PERSISTENT_CONFIG=false -e RAG_EMBEDDING_ENGINE=openai \
  -e OPENAI_API_BASE_URL=https://llm.aihosting.mittwald.de/v1 \
  -e OPENAI_API_KEY=smoke-test-not-a-real-key \
  -e RAG_OPENAI_API_BASE_URL=https://llm.aihosting.mittwald.de/v1 \
  -e RAG_OPENAI_API_KEY=smoke-test-not-a-real-key \
  -e RAG_EMBEDDING_MODEL=Qwen3-Embedding-8B \
  -e SCARF_NO_ANALYTICS=true -e DO_NOT_TRACK=true -e ANONYMIZED_TELEMETRY=false \
  "$image" bash start-mittwald.sh >/dev/null

for attempt in $(seq 1 90); do
  if docker exec "$container" sh -c 'curl -fsS http://127.0.0.1:8080/health | jq -ne "input.status == true"' >/dev/null 2>&1; then
    docker exec "$container" curl -fsS http://127.0.0.1:8080/ >/dev/null
    docker exec "$container" sh -c 'curl -fsS http://127.0.0.1:8080/api/v1/auths/signin -H "Content-Type: application/json" -d '\''{"email":"admin@example.invalid","password":"smoke-test-only-password"}'\'' | jq -ne '\''input.role == "admin"'\''' >/dev/null
    echo 'Read-only container startup and frontend passed.'
    exit 0
  fi
  if [[ "$(docker inspect -f '{{.State.Running}}' "$container")" != true ]]; then
    break
  fi
  sleep 2
done
echo 'Container startup failed.' >&2
exit 1
