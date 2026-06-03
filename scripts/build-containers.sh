#!/usr/bin/env bash
set -euo pipefail

# Build all STT Docker containers
# Usage: ./scripts/build-containers.sh [--no-cache]

EXTRA_ARGS="${*}"

echo "=== STT Container Build ==="
echo ""

echo "[1/4] Building production images (stt-server, stt-worker)..."
docker compose --profile production build ${EXTRA_ARGS} stt-server stt-worker
echo "  ✓ Production images built"
echo ""

echo "[2/4] Building ML service image (stt-ml)..."
docker compose --profile production build ${EXTRA_ARGS} stt-ml
echo "  ✓ ML service image built"
echo ""

echo "[3/4] Building dev/test images (stt-test, stt-cli)..."
docker compose --profile test build ${EXTRA_ARGS} stt-test
docker compose --profile cli build ${EXTRA_ARGS} stt-cli
echo "  ✓ Dev/test images built"
echo ""

echo "[4/4] Verifying production image has no dev/ML dependencies..."
IMAGE=$(docker compose --profile production images stt-server --format '{{.Repository}}:{{.Tag}}' 2>/dev/null | head -1)
if [ -z "$IMAGE" ]; then
    IMAGE="192.168.178.80:5000/stt-server:latest"
fi
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
echo "=== Build complete ==="
echo ""
echo "Images:"
docker image ls --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | grep -i stt | sort
echo ""
echo "Profiles:"
echo "  production  → docker compose --profile production up -d"
echo "  test        → docker compose run --rm stt-test"
echo "  cli         → docker compose --profile cli run --rm stt-cli python -m stt ..."
