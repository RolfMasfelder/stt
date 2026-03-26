#!/usr/bin/env bash
set -euo pipefail

# Deploy STT Docker image to remote host
REMOTE_HOST="192.168.178.80"
REMOTE_USER="rolf"
IMAGE_NAME="stt-app"
IMAGE_TAG="latest"
IMAGE_FILE="/tmp/stt-app.tar"

echo "=== STT Remote Deploy ==="

# Step 1: Build Docker image locally
echo "[1/3] Building Docker image..."
docker compose build stt

# Tag the image for export
docker tag "stt-${IMAGE_NAME}:${IMAGE_TAG}" "${IMAGE_NAME}:${IMAGE_TAG}" 2>/dev/null || true

# Step 2: Save and transfer image
echo "[2/3] Exporting and transferring image to ${REMOTE_USER}@${REMOTE_HOST}..."
docker save "${IMAGE_NAME}:${IMAGE_TAG}" | ssh "${REMOTE_USER}@${REMOTE_HOST}" "docker load"

# Step 3: Transfer .env and docker-compose.yml
echo "[3/3] Syncing project files..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ~/stt"
scp docker-compose.yml .env "${REMOTE_USER}@${REMOTE_HOST}:~/stt/"

echo ""
echo "=== Deploy complete ==="
echo "On ${REMOTE_HOST}, run:"
echo "  cd ~/stt && docker compose --profile production up -d stt"
