# Software Bill of Materials (SBOM) – STT

**Generated:** 3. June 2026
**Format:** CycloneDX 1.5 (JSON) + Human-Readable MD
**Generation Method:** Automated (generate-sbom.sh / generate-sbom-md.py)

## Project Overview

**STT – Lokale Meeting-Transkription und Zusammenfassung** – Speech-to-text
pipeline with speaker diarization, LLM-based summarization, and a Flutter
mobile recording client.

- **Version:** 0.1.5
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

| Component | Version | License | Purpose |
| --- | --- | --- | --- |
| boto3 | 1.43.9 | Apache-2.0 | S3-compatible object storage (ADR-11) |
| cryptography | 48.0.0 | Apache-2.0 / BSD | AES-256-GCM encryption at rest (ADR-08) |
| django | 5.2.14 | BSD-3-Clause | Web framework |
| django-cors-headers | 4.7.0 | MIT | CORS middleware |
| django-oauth-toolkit | 3.0.1 | BSD-3-Clause | OAuth2 Provider (RFC 6749/7636) |
| django-prometheus | 2.4.1 | Apache-2.0 | Prometheus metrics |
| django-q2 | 1.10.0 | MIT | Async task queue (DB broker) |
| djangorestframework | 3.16.0 | BSD-2-Clause | REST API framework |
| drf-spectacular | 0.29.0 | BSD-3-Clause | OpenAPI 3.0 schema generation |
| gunicorn | 23.0.0 | MIT | WSGI production server |
| numpy | 2.4.5 | BSD-3-Clause | Numerical operations |
| psycopg[binary] | 3.3.4 | LGPL-3.0 | PostgreSQL adapter |
| python-dotenv | 1.2.1 | BSD-3-Clause | Load .env config |
| requests | 2.32.5 | Apache-2.0 | HTTP client |

### ML Service Libraries

| Component | Version | License | Purpose |
| --- | --- | --- | --- |
| fastapi | 0.115.12 | MIT | Web framework for ML API |
| faster-whisper | 1.2.1 | MIT | Speech-to-Text (Whisper, CTranslate2) |
| numpy | 2.4.2 | BSD-3-Clause | Numerical operations |
| pyannote.audio | 4.0.4 | MIT | Speaker diarization |
| python-multipart | 0.0.20 | Apache-2.0 | Multipart file uploads |
| sounddevice | 0.5.5 | MIT | Audio I/O |
| torch | 2.11.0+cpu | BSD-3-Clause | Deep learning framework |
| torchaudio | 2.11.0+cpu | BSD-3-Clause | Audio processing for PyTorch |
| torchcodec | 0.11.0 | BSD-3-Clause | Audio/video decoding |
| uvicorn[standard] | 0.34.3 | BSD-3-Clause | — |

### Mobile App (Flutter)

| Component | Version | License | Purpose |
| --- | --- | --- | --- |
| cupertino_icons | 1.0.9 | MIT | iOS-style icons |
| http | 1.6.0 | BSD-3-Clause | HTTP client |
| http_parser | 4.1.2 | — | — |
| provider | 6.1.5+1 | MIT | State management |
| shared_preferences | 2.5.5 | BSD-3-Clause | Local key-value storage |
| record | 6.2.0 | MIT | Audio recording |
| path_provider | 2.1.5 | BSD-3-Clause | File system paths |
| intl | 0.20.2 | BSD-3-Clause | Internationalization |
| flutter_appauth | 12.0.0 | Apache-2.0 | OAuth2 / OpenID Connect client |
| flutter_secure_storage | 10.2.0 | BSD-3-Clause | Encrypted secure storage |
| crypto | 3.0.7 | — | — |
| web | 1.1.1 | — | — |
| connectivity_plus | 7.1.1 | BSD-3-Clause | Network connectivity detection |
| flutter_local_notifications | 21.0.0 | MIT | Local push notifications |
| flutter_lints | 6.0.0 | BSD-3-Clause | Lint rules |

### Infrastructure Services

| Service | Version | License | Type | Port | Purpose |
| --- | --- | --- | --- | --- | --- |
| stt-server | 0.1.5 | Proprietary | Application | 8090 | Django/DRF REST API + orchestration |
| stt-worker | 0.1.5 | Proprietary | Background | — | Celery async task processing |
| stt-ml | 0.1.5 | Proprietary | ML Service | 8091 | faster-whisper transcription + pyannote diarization |
| stt-ollama | 0.24.0 | MIT | LLM Service | 11434 | Ollama – LLM inference (mistral) |
| caddy | 2-alpine | Apache-2.0 | Infrastructure | 80/443 | Reverse proxy + automatic TLS |
| PostgreSQL | 17 | PostgreSQL License | PostgreSQL License | Database | 5432 | Primary database |
| python:3.13-slim-bookworm | 3.13 | PSF-2.0 | Infrastructure | — | Backend base image |

### Development & Quality Tools

| Component | Version | License | Purpose |
| --- | --- | --- | --- |
| pytest | 7.0 | MIT | Testing framework |
| pytest-django | 4.12.0 | BSD-3-Clause | Django integration for pytest |
| coverage | — | Apache-2.0 | Code coverage |
| ruff | 0.15.13 | MIT | Linting + formatting |
| bandit | 1.9.4 | Apache-2.0 | Security static analysis |
| pre-commit | 3.0 | MIT | Git hooks |
| factory-boy | — | MIT | Test fixtures / factories |
| responses | — | Apache-2.0 | HTTP mocking for tests |
| syft | latest | Apache-2.0 | SBOM generation (anchore/syft) |

## Machine-Readable SBOMs

CycloneDX 1.5 (JSON) files are located in `sbom/`:

| File | Component | Description |
| --- | --- | --- |
| `sbom/backend-python.cdx.json` | stt-backend | Python backend dependencies |
| `sbom/mobile-flutter.cdx.json` | stt-mobile | Flutter mobile app dependencies |
| `sbom/container-image.cdx.json` | stt-server-image | Container image layer analysis |
| `sbom/index.cdx.json` | stt (product) | Top-level index SBOM |
