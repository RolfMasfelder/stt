#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# SBOM Generation Script for STT Project
# Generates separate CycloneDX SBOMs per component + index document
#
# Components:
#   1. Backend (Python/Django)    → sbom/backend-python.cdx.json
#   2. Mobile App (Flutter/Dart)  → sbom/mobile-flutter.cdx.json
#   3. Container Image            → sbom/container-image.cdx.json
#   4. Index (Top-Level BOM)      → sbom/index.cdx.json
#
# Requirements: syft (https://github.com/anchore/syft)
#   - Uses local binary if available, otherwise runs via Docker
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SBOM_DIR="$PROJECT_ROOT/sbom"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Project version from pyproject.toml
PROJECT_VERSION="$(grep '^version' "$PROJECT_ROOT/pyproject.toml" | head -1 | cut -d'"' -f2)"

# -- Colors -------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
header(){ echo -e "\n${BLUE}━━━ $* ━━━${NC}"; }

# -- Syft detection -----------------------------------------------------------
SYFT_MODE=""  # "local" or "docker"

detect_syft() {
    if command -v syft &>/dev/null; then
        SYFT_MODE="local"
        info "Using local syft: $(syft version 2>/dev/null | head -1)"
    elif command -v docker &>/dev/null; then
        info "syft not found locally, using Docker image anchore/syft"
        docker pull -q anchore/syft:latest >/dev/null 2>&1 || true
        if docker image inspect anchore/syft:latest &>/dev/null 2>&1; then
            SYFT_MODE="docker"
        else
            error "Cannot pull anchore/syft Docker image"
            error "Install syft: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
            exit 1
        fi
    else
        error "Neither syft nor Docker found"
        error "Install syft: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin"
        exit 1
    fi
}

# Run syft with appropriate mode (local or docker)
# Usage: run_syft <source> <output_file> [extra_args...]
run_syft() {
    local source="$1"
    local output_file="$2"
    shift 2

    if [[ "$SYFT_MODE" == "local" ]]; then
        syft "$source" -o "cyclonedx-json=$output_file" "$@"
    else
        # Docker mode: mount project + docker socket, write to /out
        local filename
        filename="$(basename "$output_file")"
        local docker_args=(
            --rm
            -v "$PROJECT_ROOT:/project:ro,z"
            -v "$SBOM_DIR:/out:z"
        )
        # Mount docker socket if scanning an image
        if [[ "$source" == docker:* ]] || [[ "$source" != dir:* && "$source" != file:* ]]; then
            docker_args+=(-v /var/run/docker.sock:/var/run/docker.sock)
        fi
        # Rewrite dir: paths to /project
        local docker_source="$source"
        docker_source="${docker_source/dir:$PROJECT_ROOT/dir:\/project}"
        docker_source="${docker_source/dir:./dir:\/project}"

        docker run "${docker_args[@]}" anchore/syft:latest \
            "$docker_source" -o "cyclonedx-json=/out/$filename" "$@"
    fi
}

# -- Component SBOM generators -----------------------------------------------

generated_sboms=()

generate_backend_sbom() {
    header "Backend (Python/Django)"
    local output="$SBOM_DIR/backend-python.cdx.json"

    if [[ ! -f "$PROJECT_ROOT/requirements.txt" ]]; then
        warn "requirements.txt not found, skipping"
        return
    fi

    info "Scanning Python dependencies..."
    run_syft "dir:$PROJECT_ROOT" "$output" \
        --source-name "stt-backend" --source-version "$PROJECT_VERSION"

    if [[ -f "$output" ]]; then
        local count
        count="$(python3 -c "import json; d=json.load(open('$output')); print(len(d.get('components',[])))" 2>/dev/null || echo '?')"
        info "→ $(basename "$output") ($count components)"
        generated_sboms+=("backend-python.cdx.json")
    else
        warn "Backend SBOM generation failed"
    fi
}

generate_mobile_sbom() {
    header "Mobile App (Flutter/Dart)"
    local output="$SBOM_DIR/mobile-flutter.cdx.json"

    if [[ ! -f "$PROJECT_ROOT/mobile/pubspec.yaml" ]]; then
        warn "mobile/pubspec.yaml not found, skipping"
        return
    fi

    if [[ ! -f "$PROJECT_ROOT/mobile/pubspec.lock" ]]; then
        warn "mobile/pubspec.lock not found – run 'flutter pub get' in mobile/ first"
        warn "Scanning pubspec.yaml only (resolved versions unavailable)"
    fi

    info "Scanning Flutter/Dart dependencies..."
    run_syft "dir:$PROJECT_ROOT/mobile" "$output" \
        --source-name "stt-mobile" --source-version "$PROJECT_VERSION"

    if [[ -f "$output" ]]; then
        local count
        count="$(python3 -c "import json; d=json.load(open('$output')); print(len(d.get('components',[])))" 2>/dev/null || echo '?')"
        info "→ $(basename "$output") ($count components)"
        generated_sboms+=("mobile-flutter.cdx.json")
    else
        warn "Mobile SBOM generation failed"
    fi
}

generate_container_sbom() {
    header "Container Image (stt-server)"
    local output="$SBOM_DIR/container-image.cdx.json"
    # docker compose prefixes image name with project directory name
    local image_name="stt-stt-server:latest"

    if ! command -v docker &>/dev/null; then
        warn "Docker not available, skipping container image SBOM"
        return
    fi

    if ! docker image inspect "$image_name" &>/dev/null 2>&1; then
        warn "Image '$image_name' not found"
        warn "Build first: docker compose build stt-server"
        return
    fi

    info "Scanning container image '$image_name'..."
    if [[ "$SYFT_MODE" == "local" ]]; then
        syft "$image_name" -o "cyclonedx-json=$output"
    else
        # Export image as tar so syft container doesn't need Docker socket access
        local tmp_tar="$SBOM_DIR/.image-export.tar"
        info "Exporting image to tar (this may take a moment)..."
        docker save "$image_name" -o "$tmp_tar"
        docker run --rm \
            -v "$SBOM_DIR:/out:z" \
            anchore/syft:latest \
            "/out/.image-export.tar" -o "cyclonedx-json=/out/container-image.cdx.json"
        rm -f "$tmp_tar"
    fi

    if [[ -f "$output" ]]; then
        local count
        count="$(python3 -c "import json; d=json.load(open('$output')); print(len(d.get('components',[])))" 2>/dev/null || echo '?')"
        info "→ $(basename "$output") ($count components)"
        generated_sboms+=("container-image.cdx.json")
    else
        warn "Container image SBOM generation failed"
    fi
}

# -- Index document -----------------------------------------------------------

generate_index() {
    header "Index (Top-Level BOM)"
    local output="$SBOM_DIR/index.cdx.json"

    if [[ ${#generated_sboms[@]} -eq 0 ]]; then
        warn "No component SBOMs generated, skipping index"
        return
    fi

    # Generate index using Python for proper JSON handling
    python3 - "$SBOM_DIR" "$PROJECT_VERSION" "$TIMESTAMP" "${generated_sboms[@]}" << 'PYEOF'
import json
import sys
import uuid
from pathlib import Path

sbom_dir = Path(sys.argv[1])
version = sys.argv[2]
timestamp = sys.argv[3]
sbom_files = sys.argv[4:]

components = []
external_refs = []

component_map = {
    "backend-python.cdx.json": {
        "name": "stt-backend",
        "type": "application",
        "description": "STT Backend – Django/DRF API Server (Python)",
        "group": "stt",
    },
    "mobile-flutter.cdx.json": {
        "name": "stt-mobile",
        "type": "application",
        "description": "STT Mobile App – Audio Recording Client (Flutter/Dart)",
        "group": "stt",
    },
    "container-image.cdx.json": {
        "name": "stt-server-image",
        "type": "container",
        "description": "STT Server Container Image (python:3.13-slim-bookworm)",
        "group": "stt",
    },
}

for sbom_file in sbom_files:
    meta = component_map.get(sbom_file, {
        "name": sbom_file,
        "type": "application",
        "description": sbom_file,
        "group": "stt",
    })

    # Read component count from the SBOM
    sbom_path = sbom_dir / sbom_file
    dep_count = 0
    bom_ref = ""
    if sbom_path.exists():
        data = json.loads(sbom_path.read_text())
        dep_count = len(data.get("components", []))
        bom_ref = data.get("serialNumber", "")

    components.append({
        "type": meta["type"],
        "name": meta["name"],
        "version": version,
        "group": meta["group"],
        "description": f'{meta["description"]} ({dep_count} dependencies)',
        "bom-ref": f'component-{meta["name"]}',
    })

    external_refs.append({
        "type": "bom",
        "url": f'./{sbom_file}',
        "comment": f'CycloneDX SBOM for {meta["name"]}',
    })

index = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "serialNumber": f'urn:uuid:{uuid.uuid4()}',
    "version": 1,
    "metadata": {
        "timestamp": timestamp,
        "component": {
            "type": "application",
            "name": "stt",
            "version": version,
            "group": "stt",
            "description": "STT – Lokale Meeting-Transkription und Zusammenfassung (Product-Level SBOM Index)",
        },
        "tools": [{"name": "generate-sbom.sh", "version": "1.0.0"}],
    },
    "components": components,
    "externalReferences": external_refs,
}

output = sbom_dir / "index.cdx.json"
output.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
print(f"Generated index with {len(components)} component references")
PYEOF

    if [[ -f "$output" ]]; then
        info "→ $(basename "$output") (${#generated_sboms[@]} component BOMs)"
    fi
}

# -- Main ---------------------------------------------------------------------

main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════╗"
    echo "║   STT Project – SBOM Generator        ║"
    echo "║   Format: CycloneDX 1.5 (JSON)        ║"
    echo "╚═══════════════════════════════════════╝"
    echo -e "${NC}"

    info "Project version: $PROJECT_VERSION"
    info "Timestamp:       $TIMESTAMP"
    info "Output:          $SBOM_DIR/"
    echo

    # Ensure output directory
    mkdir -p "$SBOM_DIR"

    # Detect syft
    detect_syft

    # Generate component SBOMs
    generate_backend_sbom
    generate_mobile_sbom
    generate_container_sbom

    # Generate index
    generate_index

    # Summary
    header "Summary"
    if [[ ${#generated_sboms[@]} -gt 0 ]]; then
        info "Generated ${#generated_sboms[@]} component SBOM(s) + index:"
        for f in "${generated_sboms[@]}"; do
            local size
            size="$(du -h "$SBOM_DIR/$f" 2>/dev/null | cut -f1)"
            echo -e "  ${GREEN}✓${NC} $f ($size)"
        done
        echo -e "  ${GREEN}✓${NC} index.cdx.json"
        echo
        info "Files in $SBOM_DIR/ – commit to git for versioning"
    else
        warn "No SBOMs were generated"
    fi
}

main "$@"
