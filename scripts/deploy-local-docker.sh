#!/usr/bin/env bash
set -euo pipefail

# Deploy STT Docker stack locally via docker compose.
# Builds images with versioned tag, starts the production stack,
# fetches the Caddy TLS CA certificate, and bootstraps OAuth2.
#
# Usage: ./scripts/deploy-local-docker.sh [--no-cache]

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

echo "=== STT Local Docker Deploy (tag: ${TAG}) ==="
echo "    OAuth2 client: ${OAUTH2_CLIENT_ID}"
echo "    LLM model:     ${LLM_MODEL}"
echo ""

# Step 1: Build Docker images
echo "[1/6] Building Docker images (tag: ${TAG})..."
IMAGE_TAG=${TAG} docker compose build ${EXTRA_ARGS} stt-server stt-ml
echo "  ✓ Images built"
echo ""

# Step 2: Start production stack locally (SITE_ADDRESS=localhost overrides .env)
echo "[2/6] Starting production stack locally..."
IMAGE_TAG=${TAG} SITE_ADDRESS=localhost docker compose --profile production up -d --no-build
echo "  ✓ Stack started"
echo ""

# Step 3: Run database migrations
echo "[3/6] Running database migrations..."
docker compose exec stt-server python manage.py migrate --noinput
echo "  ✓ Migrations applied"
echo ""

# Step 4: Pull Ollama LLM model (idempotent — no-op if already present)
echo "[4/6] Ensuring Ollama model '${LLM_MODEL}' is available..."
OLLAMA_CONTAINER=$(docker ps -q --filter name=stt-ollama 2>/dev/null | head -1 || true)
if [[ -z "${OLLAMA_CONTAINER}" ]]; then
  echo "  ⚠ Ollama container not running — skipping model pull"
else
  docker exec "${OLLAMA_CONTAINER}" ollama pull "${LLM_MODEL}"
  echo "  ✓ Model '${LLM_MODEL}' ready"
fi
echo ""

# Step 5: Fetch Caddy CA certificate (retry up to 30s for Caddy to initialise)
echo "[5/6] Fetching Caddy CA certificate..."
for i in $(seq 1 30); do
  if docker exec stt-caddy test -f /data/caddy/pki/authorities/local/root.crt 2>/dev/null; then
    docker exec stt-caddy cat /data/caddy/pki/authorities/local/root.crt > caddy-root.crt
    echo "  ✓ Saved to caddy-root.crt"
    break
  fi
  [[ $i -eq 30 ]] && echo "  ✗ Caddy CA cert not available after 30s" >&2 && exit 1
  echo "  Waiting for Caddy CA (${i}/30)..."
  sleep 1
done
echo ""

# Step 6: Bootstrap OAuth2 application (idempotent — creates only if missing)
echo "[6/6] Bootstrapping OAuth2 application (${OAUTH2_CLIENT_ID})..."
docker exec -i \
  -e "OAUTH2_CLIENT_ID=${OAUTH2_CLIENT_ID}" \
  -e "OAUTH2_CLIENT_SECRET=${OAUTH2_CLIENT_SECRET}" \
  stt-server python << 'PYEOF'
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
echo "=== Local Deploy complete (tag: ${TAG}) ==="
echo "Verify with: docker ps"
echo ""
echo "Run CLI:"
echo "  REQUESTS_CA_BUNDLE=\$PWD/caddy-root.crt \\"
echo "  STT_SERVER_URL=https://localhost \\"
echo "  OAUTH2_CLIENT_ID=${OAUTH2_CLIENT_ID} \\"
echo "  IMAGE_TAG=${TAG} \\"
echo "  docker compose --profile cli run --rm stt-cli python -m stt <audio-file>"
