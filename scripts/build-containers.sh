#!/usr/bin/env bash
set -euo pipefail

# Build all STT Docker containers
# Usage: ./scripts/build-containers.sh [--no-cache]

EXTRA_ARGS="${*}"

# Versioned tag — same formula as deploy-remote-docker.sh
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
GIT_SHA=$(git rev-parse --short HEAD)
IMAGE_TAG="v${VERSION}-${GIT_SHA}"

echo "=== STT Container Build (tag: ${IMAGE_TAG}) ==="
echo ""

echo "[1/4] Building production images (stt-server, stt-worker)..."
IMAGE_TAG=${IMAGE_TAG} docker compose --profile production build ${EXTRA_ARGS} stt-server stt-worker
echo "  ✓ Production images built"
echo ""

echo "[2/4] Building ML service image (stt-ml)..."
IMAGE_TAG=${IMAGE_TAG} docker compose --profile production build ${EXTRA_ARGS} stt-ml
echo "  ✓ ML service image built"
echo ""

echo "[3/4] Building dev/test images (stt-test, stt-cli)..."
IMAGE_TAG=${IMAGE_TAG} docker compose --profile test build ${EXTRA_ARGS} stt-test
IMAGE_TAG=${IMAGE_TAG} docker compose --profile cli build ${EXTRA_ARGS} stt-cli
echo "  ✓ Dev/test images built"
echo ""

echo "[4/4] Verifying production image has no dev/ML dependencies..."
IMAGE="192.168.178.80:5000/stt-server:${IMAGE_TAG}"
docker run --rm "$IMAGE" python -c "
try:
    import pytest
    print('  ✗ FAIL: pytest found in production image')
    exit(1)
except ImportError:
    print('  ✓ No dev dependencies in production image')
try:
    import torch
    print('  ✗ FAIL: torch found in production image')
    exit(1)
except ImportError:
    print('  ✓ No ML dependencies in production image (torch/pyannote in stt-ml)')
"

echo ""
echo "=== Build complete (tag: ${IMAGE_TAG}) ==="
echo ""
echo "Images:"
docker image ls --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep -i stt | sort
echo ""
echo "Profiles:"
echo "  production  → docker compose --profile production up -d"
echo "  test        → docker compose run --rm stt-test"
echo "  cli         → docker compose --profile cli run --rm stt-cli python -m stt ..."
