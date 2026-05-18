#!/usr/bin/env python3
"""
Generate docs/SBOM.md – human-readable Software Bill of Materials for STT.

Usage:
    python scripts/generate-sbom-md.py

Reads:
  - requirements.txt                 (backend Python deps)
  - services/ml/requirements.txt     (ML service deps)
  - mobile/pubspec.yaml              (Flutter deps)
  - pyproject.toml                   (project version)

Writes:
  - docs/SBOM.md
"""

import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Known licenses for packages not easily detectable from requirements.txt
# ---------------------------------------------------------------------------
KNOWN_LICENSES: dict[str, str] = {
    # Backend
    "boto3": "Apache-2.0",
    "cryptography": "Apache-2.0 / BSD",
    "django": "BSD-3-Clause",
    "django-cors-headers": "MIT",
    "django-oauth-toolkit": "BSD-3-Clause",
    "django-prometheus": "Apache-2.0",
    "django-q2": "MIT",
    "djangorestframework": "BSD-2-Clause",
    "drf-spectacular": "BSD-3-Clause",
    "gunicorn": "MIT",
    "numpy": "BSD-3-Clause",
    "psycopg": "LGPL-3.0",
    "psycopg[binary]": "LGPL-3.0",
    "python-dotenv": "BSD-3-Clause",
    "requests": "Apache-2.0",
    # ML service
    "fastapi": "MIT",
    "faster-whisper": "MIT",
    "pyannote.audio": "MIT",
    "python-multipart": "Apache-2.0",
    "sounddevice": "MIT",
    "torch": "BSD-3-Clause",
    "torchaudio": "BSD-3-Clause",
    "torchcodec": "BSD-3-Clause",
    "uvicorn": "BSD-3-Clause",
    # Dev tools (from pyproject.toml)
    "pytest": "MIT",
    "pytest-django": "BSD-3-Clause",
    "coverage": "Apache-2.0",
    "ruff": "MIT",
    "bandit": "Apache-2.0",
    "pre-commit": "MIT",
    "factory-boy": "MIT",
    "responses": "Apache-2.0",
    # Flutter (pubspec.yaml)
    "http": "BSD-3-Clause",
    "provider": "MIT",
    "shared_preferences": "BSD-3-Clause",
    "record": "MIT",
    "path_provider": "BSD-3-Clause",
    "intl": "BSD-3-Clause",
    "flutter_appauth": "Apache-2.0",
    "flutter_secure_storage": "BSD-3-Clause",
    "connectivity_plus": "BSD-3-Clause",
    "flutter_local_notifications": "MIT",
    "cupertino_icons": "MIT",
    "flutter_lints": "BSD-3-Clause",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    """Parse requirements.txt → [(name, version), ...]."""
    result = []
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        # Handle extras like psycopg[binary]==3.3.4
        m = re.match(r"^([A-Za-z0-9_.+-]+(?:\[[^\]]+\])?)[=<>!~]+([^\s,;]+)", line)
        if m:
            name, version = m.group(1), m.group(2)
            result.append((name, version))
    return result


def parse_pubspec(path: Path) -> list[tuple[str, str]]:
    """Parse pubspec.yaml deps → [(name, version_constraint), ...]."""
    result = []
    in_deps = False
    for line in path.read_text().splitlines():
        if re.match(r"^(dependencies|dev_dependencies):", line):
            in_deps = True
            continue
        if in_deps and re.match(r"^\S", line) and not re.match(r"^\s", line):
            in_deps = False
        if in_deps:
            m = re.match(r"^\s{2}([a-z_][a-z0-9_-]*):\s*(.+)", line)
            if m:
                name, version = m.group(1).strip(), m.group(2).strip()
                if name in ("flutter",):
                    continue
                # Remove quotes
                version = version.strip("\"'")
                result.append((name, version))
    return result


def get_version(project_root: Path) -> str:
    text = (project_root / "pyproject.toml").read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "unknown"


def license_of(name: str) -> str:
    base_name = name.split("[")[0].lower()
    for key, lic in KNOWN_LICENSES.items():
        if key.lower() == base_name or key.lower() == name.lower():
            return lic
    return "—"


def md_table(rows: list[tuple[str, ...]], headers: list[str]) -> str:
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    head = "| " + " | ".join(headers) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return f"{head}\n{sep}\n{body}"


# ---------------------------------------------------------------------------
# SBOM.md content builders
# ---------------------------------------------------------------------------

BACKEND_PURPOSES: dict[str, str] = {
    "boto3": "S3-compatible object storage (ADR-11)",
    "cryptography": "AES-256-GCM encryption at rest (ADR-08)",
    "django": "Web framework",
    "django-cors-headers": "CORS middleware",
    "django-oauth-toolkit": "OAuth2 Provider (RFC 6749/7636)",
    "django-prometheus": "Prometheus metrics",
    "django-q2": "Async task queue (DB broker)",
    "djangorestframework": "REST API framework",
    "drf-spectacular": "OpenAPI 3.0 schema generation",
    "gunicorn": "WSGI production server",
    "numpy": "Numerical operations",
    "psycopg": "PostgreSQL adapter",
    "psycopg[binary]": "PostgreSQL adapter",
    "python-dotenv": "Load .env config",
    "requests": "HTTP client",
}

ML_PURPOSES: dict[str, str] = {
    "fastapi": "Web framework for ML API",
    "faster-whisper": "Speech-to-Text (Whisper, CTranslate2)",
    "numpy": "Numerical operations",
    "pyannote.audio": "Speaker diarization",
    "python-multipart": "Multipart file uploads",
    "sounddevice": "Audio I/O",
    "torch": "Deep learning framework",
    "torchaudio": "Audio processing for PyTorch",
    "torchcodec": "Audio/video decoding",
    "uvicorn": "ASGI server",
}

FLUTTER_PURPOSES: dict[str, str] = {
    "cupertino_icons": "iOS-style icons",
    "http": "HTTP client",
    "provider": "State management",
    "shared_preferences": "Local key-value storage",
    "record": "Audio recording",
    "path_provider": "File system paths",
    "intl": "Internationalization",
    "flutter_appauth": "OAuth2 / OpenID Connect client",
    "flutter_secure_storage": "Encrypted secure storage",
    "connectivity_plus": "Network connectivity detection",
    "flutter_local_notifications": "Local push notifications",
    "flutter_lints": "Lint rules",
}


def build_md(project_root: Path) -> str:
    version = get_version(project_root)
    now = datetime.now(UTC).strftime("%-d. %B %Y")

    backend_deps = parse_requirements(project_root / "requirements.txt")
    ml_deps = parse_requirements(project_root / "services" / "ml" / "requirements.txt")
    flutter_deps = parse_pubspec(project_root / "mobile" / "pubspec.yaml")

    def backend_rows() -> list[tuple[str, ...]]:
        rows = []
        for name, ver in sorted(backend_deps, key=lambda x: x[0].lower()):
            purpose = BACKEND_PURPOSES.get(
                name, BACKEND_PURPOSES.get(name.split("[")[0], "—")
            )
            rows.append((name, ver, license_of(name), purpose))
        return rows

    def ml_rows() -> list[tuple[str, ...]]:
        rows = []
        for name, ver in sorted(ml_deps, key=lambda x: x[0].lower()):
            purpose = ML_PURPOSES.get(name, "—")
            rows.append((name, ver, license_of(name), purpose))
        return rows

    def flutter_rows() -> list[tuple[str, ...]]:
        rows = []
        for name, ver in flutter_deps:
            if name in ("flutter", "integration_test", "flutter_test"):
                continue
            purpose = FLUTTER_PURPOSES.get(name, "—")
            rows.append((name, ver, license_of(name), purpose))
        return rows

    backend_table = md_table(
        backend_rows(), ["Component", "Version", "License", "Purpose"]
    )
    ml_table = md_table(ml_rows(), ["Component", "Version", "License", "Purpose"])
    flutter_table = md_table(
        flutter_rows(), ["Component", "Version", "License", "Purpose"]
    )

    infra_rows = [
        (
            "stt-server",
            version,
            "Application",
            "8090",
            "Django/DRF REST API + orchestration",
        ),
        ("stt-worker", version, "Background", "—", "Celery async task processing"),
        (
            "stt-ml",
            version,
            "ML Service",
            "8091",
            "faster-whisper transcription + pyannote diarization",
        ),
        (
            "stt-ollama",
            "0.24.0",
            "LLM Service",
            "11434",
            "Ollama – LLM inference (mistral)",
        ),
        (
            "caddy",
            "2-alpine",
            "Infrastructure",
            "80/443",
            "Reverse proxy + automatic TLS",
        ),
        ("PostgreSQL", "17", "Database", "5432", "Primary database"),
        (
            "python:3.13-slim-bookworm",
            "3.13",
            "Infrastructure",
            "—",
            "Backend base image",
        ),
    ]
    infra_table = md_table(
        infra_rows, ["Service", "Version", "Type", "Port", "Purpose"]
    )

    dev_rows = [
        ("pytest", "—", "MIT", "Testing framework"),
        ("pytest-django", "—", "BSD-3-Clause", "Django integration for pytest"),
        ("coverage", "—", "Apache-2.0", "Code coverage"),
        ("ruff", "—", "MIT", "Linting + formatting"),
        ("bandit", "—", "Apache-2.0", "Security static analysis"),
        ("pre-commit", "—", "MIT", "Git hooks"),
        ("factory-boy", "—", "MIT", "Test fixtures / factories"),
        ("responses", "—", "Apache-2.0", "HTTP mocking for tests"),
        ("syft", "latest", "Apache-2.0", "SBOM generation (anchore/syft)"),
    ]
    # Pull actual versions from pyproject.toml dev deps where possible
    pyproject_text = (project_root / "pyproject.toml").read_text()
    for i, (name, _ver, lic, purpose) in enumerate(dev_rows):
        m = re.search(
            rf'"{re.escape(name)}[>=<!\["][^"]*"', pyproject_text, re.IGNORECASE
        )
        if m:
            vm = re.search(r"[>=<~!]+([0-9][^\s\",']+)", m.group())
            if vm:
                dev_rows[i] = (name, vm.group(1), lic, purpose)
    dev_table = md_table(dev_rows, ["Component", "Version", "License", "Purpose"])

    return f"""\
# Software Bill of Materials (SBOM) – STT

**Generated:** {now}
**Format:** CycloneDX 1.5 (JSON) + Human-Readable MD
**Generation Method:** Automated (generate-sbom.sh / generate-sbom-md.py)

## Project Overview

**STT – Lokale Meeting-Transkription und Zusammenfassung** – Speech-to-text
pipeline with speaker diarization, LLM-based summarization, and a Flutter
mobile recording client.

- **Version:** {version}
- **Architecture:** Three-service: Django/DRF API + FastAPI ML microservice + Ollama LLM
- **Deployment:** Docker Compose (Production) / k3s (Kubernetes)
- **Machine learning:** faster-whisper (CTranslate2) + pyannote.audio

## Core Technologies

### Runtime Environment

- **Backend:** Python 3.13 (Django/DRF, Gunicorn)
- **ML Service:** Python 3.13 (FastAPI, uvicorn)
- **LLM:** Ollama 0.24.0 (mistral model)
- **Base OS:** Debian Bookworm (slim)
- **Mobile:** Flutter / Dart (Android + iOS)
- **Deployment:** Docker Compose (Production) / k3s (Kubernetes)

### Backend Framework & Core Libraries

{backend_table}

### ML Service Libraries

{ml_table}

### Mobile App (Flutter)

{flutter_table}

### Infrastructure Services

{infra_table}

### Development & Quality Tools

{dev_table}

## Machine-Readable SBOMs

CycloneDX 1.5 (JSON) files are located in `sbom/`:

| File | Component | Description |
| --- | --- | --- |
| `sbom/backend-python.cdx.json` | stt-backend | Python backend dependencies |
| `sbom/mobile-flutter.cdx.json` | stt-mobile | Flutter mobile app dependencies |
| `sbom/container-image.cdx.json` | stt-server-image | Container image layer analysis |
| `sbom/index.cdx.json` | stt (product) | Top-level index SBOM |
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    output = project_root / "docs" / "SBOM.md"

    content = build_md(project_root)
    output.write_text(content, encoding="utf-8")
    sys.stdout.write(f"Generated {output.relative_to(project_root)}\n")


if __name__ == "__main__":
    main()
