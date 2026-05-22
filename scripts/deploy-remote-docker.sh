#!/usr/bin/env bash
set -euo pipefail

# Deploy STT Docker images to cirrus7-neu via registry + docker compose.
# Builds images locally, pushes to the local registry, pulls on the remote,
# restarts the production stack, and bootstraps Caddy TLS + OAuth2.
#
# Usage: ./scripts/deploy-remote-docker.sh [--no-cache]

REGISTRY="192.168.178.80:5000"
REMOTE_HOST="192.168.178.80"
REMOTE_USER="rolf"
REMOTE_DIR="~/workspace/STT"
EXTRA_ARGS="${*}"

# Build versioned tag: v<version>-<git-sha>
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
GIT_SHA=$(git rev-parse --short HEAD)
TAG="v${VERSION}-${GIT_SHA}"

# Read OAuth2 CLI client credentials from .env (with defaults)
OAUTH2_CLIENT_ID=$(python -c "
import re, pathlib
try:
    m = re.search(r'^OAUTH2_CLIENT_ID=(.+)$', pathlib.Path('.env').read_text(), re.M)
    print(m.group(1).strip().strip('\"').strip(\"'\")) if m else print('stt-cli-client')
except: print('stt-cli-client')
")
OAUTH2_CLIENT_SECRET=$(python -c "
import re, pathlib
try:
    m = re.search(r'^OAUTH2_CLIENT_SECRET=(.+)$', pathlib.Path('.env').read_text(), re.M)
    print(m.group(1).strip().strip('\"').strip(\"'\")) if m else print('stt-cli-secret')
except: print('stt-cli-secret')
")

LLM_MODEL=$(grep -E '^LLM_MODEL=' .env 2>/dev/null | cut -d= -f2 | tr -d '"' || true)
LLM_MODEL="${LLM_MODEL:-mistral}"

echo "=== STT Docker Deploy (tag: ${TAG}) ==="
echo "    OAuth2 client: ${OAUTH2_CLIENT_ID}"
echo "    LLM model:     ${LLM_MODEL}"

# Step 1: Build Docker images — IMAGE_TAG ensures correct names from the start
echo "[1/8] Building Docker images (tag: ${TAG})..."
IMAGE_TAG=${TAG} docker compose build ${EXTRA_ARGS} stt-server stt-ml

# Step 2: Push to registry (no separate tagging needed — build already named correctly)
echo "[2/8] Pushing images to registry..."
docker push "${REGISTRY}/stt-server:${TAG}"
docker push "${REGISTRY}/stt-ml:${TAG}"

# Step 3: Sync docker-compose.yml and pull images on remote
echo "[3/8] Syncing docker-compose.yml and pulling images on ${REMOTE_HOST}..."
scp docker-compose.yml "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/docker-compose.yml"
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
  docker pull ${REGISTRY}/stt-server:${TAG} &&
  docker pull ${REGISTRY}/stt-ml:${TAG}
"

# Step 4: Restart production stack with the versioned tag (no rebuild)
echo "[4/8] Restarting production stack on ${REMOTE_HOST}..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
  cd ${REMOTE_DIR} &&
  IMAGE_TAG=${TAG} docker compose --profile production up -d --no-build
"

# Step 5: Run database migrations on remote
echo "[5/8] Running database migrations on ${REMOTE_HOST}..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" \
  "cd ${REMOTE_DIR} && docker compose exec stt-server python manage.py migrate --noinput"
echo "  ✓ Migrations applied"

# Step 6: Pull Ollama LLM model on remote (idempotent — no-op if already present)
echo "[6/8] Ensuring Ollama model '${LLM_MODEL}' is available on ${REMOTE_HOST}..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "
  OLLAMA_CONTAINER=\$(docker ps -q --filter name=stt-ollama 2>/dev/null | head -1 || true)
  if [[ -n \"\${OLLAMA_CONTAINER}\" ]]; then
    docker exec \"\${OLLAMA_CONTAINER}\" ollama pull ${LLM_MODEL}
    echo '  ✓ Model ${LLM_MODEL} ready'
  else
    echo '  ⚠ Ollama container not running — skipping model pull'
  fi
"

# Step 7: Fetch Caddy CA certificate (retry up to 30s for Caddy to initialise)
echo "[7/8] Fetching Caddy CA certificate..."
for i in $(seq 1 30); do
  if ssh "${REMOTE_USER}@${REMOTE_HOST}" \
       "docker exec stt-caddy test -f /data/caddy/pki/authorities/local/root.crt" 2>/dev/null; then
    ssh "${REMOTE_USER}@${REMOTE_HOST}" \
      "docker exec stt-caddy cat /data/caddy/pki/authorities/local/root.crt" > caddy-root.crt
    echo "  ✓ Saved to caddy-root.crt"
    break
  fi
  [[ $i -eq 30 ]] && echo "  ✗ Caddy CA cert not available after 30s" >&2 && exit 1
  echo "  Waiting for Caddy CA (${i}/30)..."
  sleep 1
done

# Step 8: Bootstrap OAuth2 application on remote (idempotent — creates only if missing)
echo "[8/8] Bootstrapping OAuth2 application (${OAUTH2_CLIENT_ID})..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" \
  "docker exec -i \
     -e \"OAUTH2_CLIENT_ID=${OAUTH2_CLIENT_ID}\" \
     -e \"OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET}\" \
     stt-server python" << 'PYEOF'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stt.settings')
django.setup()
from django.contrib.auth.models import User
from oauth2_provider.models import Application
client_id = os.environ.get('OAUTH2_CLIENT_ID', 'stt-cli-client')
client_secret = os.environ.get('OAUTH2_CLIENT_SECRET', 'stt-cli-secret')
if Application.objects.filter(client_id=client_id).exists():
    print('OAuth2 app already exists: ' + client_id)
else:
    u = User.objects.filter(is_superuser=True).first()
    if not u:
        u = User.objects.create_superuser('admin', '', 'admin')
        print('Created superuser: admin')
    Application.objects.create(
        client_id=client_id,
        user=u,
        name='STT CLI',
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        client_secret=client_secret,
    )
    print('OAuth2 app created: ' + client_id)
PYEOF

echo ""
echo "=== Docker Deploy complete (tag: ${TAG}) ==="
echo "Verify with: ssh ${REMOTE_USER}@${REMOTE_HOST} 'docker ps'"
echo ""
echo "Run CLI:"
echo "  REQUESTS_CA_BUNDLE=/app/caddy-root.crt \\"
echo "  STT_SERVER_URL=https://${REMOTE_HOST} \\"
echo "  OAUTH2_CLIENT_ID=${OAUTH2_CLIENT_ID} \\"
echo "  docker compose --profile cli run --rm stt-cli python -m stt <audio-file>"
