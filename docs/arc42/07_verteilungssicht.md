# 7. Verteilungssicht

## Deployment-Topologie

```
┌─────────────────────────────────┐     ┌─────────────────────────────────────┐
│  Lokaler Rechner                │     │  Remote-Server 192.168.178.80       │
│  (openSUSE, kein GPU)           │     │  (Linux, optional GPU)              │
│                                 │     │                                     │
│  ┌───────────────────────┐      │     │  ┌─────────────────────────────┐    │
│  │  python -m stt        │      │     │  │  Docker: stt-server         │    │
│  │  (venv oder Docker)   │──────┤     │  │  Port 8001                  │    │
│  │                       │  HTTP│     │  │  FastAPI + transcribe +     │    │
│  │  STT_SERVER_URL=      │      │     │  │  diarize + summarize        │    │
│  │  http://...80:8001    │      │     │  └──────────┬──────────────────┘    │
│  └───────────────────────┘      │     │             │                       │
│                                 │     │  ┌──────────▼──────────────────┐    │
│  ┌───────────────────────┐      │     │  │  LM Studio (nativ)         │    │
│  │  data/                │      │     │  │  Port 1234                  │    │
│  │  ├── audio/ (Eingabe) │      │     │  │  Modell: glm-4.7-flash     │    │
│  │  └── output/ (Ergebn.)│      │     │  └─────────────────────────────┘    │
│  └───────────────────────┘      │     │                                     │
│                                 │     │  ┌─────────────────────────────┐    │
└─────────────────────────────────┘     │  │  faster-whisper-server      │    │
                                        │  │  Port 8000 (optional)       │    │
                                        │  └─────────────────────────────┘    │
                                        └─────────────────────────────────────┘
```

## Docker-Services

| Service | Profil | Zweck | Image |
|---------|--------|-------|-------|
| `stt-server` | production | Django/DRF-Server, Port 8090 | Eigenes Dockerfile |
| `stt-worker` | production | django-q2 Task-Worker | Eigenes Dockerfile |
| `stt-ml` | production | ML-Service: Transkription + Diarization, Port 8091 | Eigenes Dockerfile |
| `stt-ollama` | production | Ollama LLM-Inferenz, Port 11434 | `ollama/ollama:0.24.0` |
| `db` | production | PostgreSQL-Datenbank | `postgres:17` |
| `caddy` | production | Reverse-Proxy + TLS-Terminierung | `caddy:2-alpine` |
| `stt-test` | test | pytest-Runner | Eigenes Dockerfile (dev) |
| `stt-cli` | cli | CLI-Tool | Eigenes Dockerfile (dev) |
| `whisper-server` | whisper-remote | Alternativer Whisper-Server | `fedirz/faster-whisper-server:latest-cpu` |
| `flutter` | mobile | Flutter-Entwicklung | Eigenes Dockerfile |

## Kubernetes-Deployment (k3s)

Produktivbetrieb auf `cirrus7-neu` (192.168.178.80, 64 GB RAM, 32 CPUs) im
Namespace `stt`. Alle Pods laufen via `nodeSelector: kubernetes.io/hostname: cirrus7-neu`.

### Pods

| Pod | Image | Zweck |
|-----|-------|-------|
| `stt-stt-server` | `stt-server:v<ver>` | Django/DRF REST-API, Port 8090 |
| `stt-stt-worker` | `stt-server:v<ver>` | Django-Q2 Async-Worker |
| `stt-stt-ml` | `stt-ml:v<ver>` | FastAPI ML-Service (Whisper + pyannote), Port 8091 |
| `ollama` | `ollama/ollama` | LLM-Inferenz für Zusammenfassung, Port 11434 |
| `postgres` | `postgres:17` | PostgreSQL-Datenbank |
| `minio` | `minio/minio` | S3-kompatibler Objektspeicher |

### Ingress

Caddy läuft als Docker-Container im `production`-Profil und übernimmt TLS-Terminierung (Port 443/80). Nginx-Ingress-Controller im Namespace `ingress-nginx` für k3s.
Extern erreichbar unter `http://stt.local` (DNS/hosts-Eintrag erforderlich).

### Persistent Volumes

| PVC | Größe | Mount | Zweck |
|-----|-------|-------|-------|
| `postgres-data` | 5 Gi | `/var/lib/postgresql/data` | Datenbank |
| `minio-data` | 10 Gi | `/data` | Audio-Dateien + Ergebnisse |
| `ollama-data` | 20 Gi | `/root/.ollama` | LLM-Modelle |
| `stt-stt-ml-cache` | 10 Gi | `/root/.cache/huggingface` | Whisper + pyannote-Modelle |

Der PVC `stt-stt-ml-cache` verhindert, dass pyannote-Modelle (~1 GB) bei jedem
Pod-Neustart neu heruntergeladen werden. Wegen `ReadWriteOnce` wird die
Deployment-Strategy auf `Recreate` gesetzt wenn `persistence.enabled: true`.

### HuggingFace-Token (pyannote-Diarisierung)

pyannote/speaker-diarization-3.1 ist ein gated Model. Der Token wird in einem
**extern verwalteten** Secret gespeichert (nicht von Helm verwaltet):

```bash
kubectl create secret generic stt-stt-ml-config -n stt \
  --from-literal=HF_STT_TOKEN=<token>
```

Das Secret wird in `values-k3s.yaml` via `mlService.existingHfTokenSecret` referenziert.
Alternativ kann Helm das Secret selbst verwalten indem `hfToken: <token>` gesetzt wird
(nicht für git-tracked Dateien geeignet).

### Helm-Deployment

```bash
helm upgrade stt k8s/helm/stt/ -n stt \
  -f k8s/helm/values-k3s.yaml \
  --set image.tag=v<ver>-<sha> \
  --set mlService.image.tag=v<ver>-<sha> \
  --insecure-skip-tls-verify
```
