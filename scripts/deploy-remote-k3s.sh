#!/usr/bin/env bash
set -euo pipefail

# Deploy STT Docker images to local registry and upgrade k3s via Helm
REGISTRY="192.168.178.80:5000"

# Build versioned tag: v<version>-<git-sha>
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
GIT_SHA=$(git rev-parse --short HEAD)
TAG="v${VERSION}-${GIT_SHA}"

echo "=== STT k3s Deploy (tag: ${TAG}) ==="

# Step 1: Build Docker images
echo "[1/4] Building Docker images..."
docker compose build stt-server stt-ml

# Step 2: Tag for registry
echo "[2/4] Tagging images for registry ${REGISTRY}..."
docker tag stt-stt-server:latest "${REGISTRY}/stt-server:${TAG}"
docker tag stt-stt-ml:latest "${REGISTRY}/stt-ml:${TAG}"

# Step 3: Push to registry
echo "[3/4] Pushing images to registry..."
docker push "${REGISTRY}/stt-server:${TAG}"
docker push "${REGISTRY}/stt-ml:${TAG}"

# Step 4: Deploy via Helm
echo "[4/4] Upgrading Helm release on k3s..."
helm upgrade stt k8s/helm/stt/ -n stt -f k8s/helm/values-k3s.yaml \
  --set image.tag="${TAG}" \
  --set mlService.image.tag="${TAG}"

echo ""
echo "=== k3s Deploy complete (tag: ${TAG}) ==="
echo "Verify with: kubectl get pods -n stt"
