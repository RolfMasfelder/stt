# Anwendungsübersicht und Schnittstellen

## Gesamtübersicht

```txt
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              STT-System                                          │
│                                                                                  │
│  ┌──────────────────────┐           ┌──────────────────────────────────────────┐  │
│  │  Lokaler Rechner     │   HTTP    │   Docker-Compose-Umgebung               │  │
│  │                      │           │                                          │  │
│  │  ┌────────────────┐  │           │  ┌──────────────────────────────────┐    │  │
│  │  │ CLI            │  │ ┌──────┐  │  │  Django/DRF (stt-server) :8090  │    │  │
│  │  │ (__main__.py)  │  │ │ REST │  │  │                                  │    │  │
│  │  │                │──┼►│ API  │──┼─►│  /health           [GET]        │    │  │
│  │  │ --diarize      │  │ │      │  │  │  /v1/transcribe   [POST]        │    │  │
│  │  │ --process      │◄─┼─│      │◄─┼──│  /v1/diarize      [POST]        │    │  │
│  │  │ --summarize    │  │ └──────┘  │  │  /v1/process      [POST]        │    │  │
│  │  │ --skip         │  │           │  │  /v1/jobs         [POST/GET]    │    │  │
│  │  └──────┬─────────┘  │           │  └───────┬──────────┬───────────┘    │  │
│  │         │            │           │          │          │                │  │
│  │  ┌──────▼─────────┐  │           │  ┌───────▼──┐  ┌───▼────────────┐   │  │
│  │  │ client.py      │  │           │  │ HTTP-    │  │ summarize.py   │   │  │
│  │  │ (STTClient)    │  │           │  │ Clients  │  │ (LLM-Client)   │   │  │
│  │  └────────────────┘  │           │  │          │  └───┬────────────┘   │  │
│  │                      │           │  │transcribe│      │               │  │
│  │  ┌────────────────┐  │           │  │  .py     │      │               │  │
│  │  │ data/          │  │           │  │diarize   │      │               │  │
│  │  │ ├── audio/     │  │           │  │  .py     │      │               │  │
│  │  │ └── output/    │  │           │  └───────┬──┘  ┌───▼────────────┐   │  │
│  │  └────────────────┘  │           │          │     │ LLM-Service    │   │  │
│  └──────────────────────┘           │          │     │ (Ollama/:11434)│   │  │
│                                     │          │     └────────────────┘   │  │
│                                     │  ┌───────▼──────────────────────┐   │  │
│                                     │  │  ML-Service (stt-ml) :8091  │   │  │
│                                     │  │  FastAPI-Microservice       │   │  │
│                                     │  │                              │   │  │
│                                     │  │  /v1/transcribe  [POST]     │   │  │
│                                     │  │  /v1/diarize     [POST]     │   │  │
│                                     │  │  /health         [GET]      │   │  │
│                                     │  │                              │   │  │
│                                     │  │  ┌────────────┐ ┌─────────┐ │   │  │
│                                     │  │  │faster-     │ │pyannote │ │   │  │
│                                     │  │  │whisper     │ │.audio   │ │   │  │
│                                     │  │  │(lokal)     │ │(lokal)  │ │   │  │
│                                     │  │  └────────────┘ └─────────┘ │   │  │
│                                     │  └──────────────────────────────┘   │  │
│                                     └──────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

## Schnittstellen im Detail

### S1: STT Server REST-API (Django/DRF, Port 8090)

Definiert in [`openapi.json`](../openapi.json). Django fungiert als dünner HTTP-Client —
ML-Inferenz wird an den ML-Service (S2) delegiert.

| Endpoint | Methode | Request | Response | Beschreibung |
|----------|---------|---------|----------|--------------|
| `/health` | GET | — | `{"status": "ok"}` | Health-Check |
| `/v1/transcribe` | POST | `file` (multipart), `model` (form) | `{"text": "..."}` | Audio → Text |
| `/v1/diarize` | POST | `file` (multipart), `model` (form) | `{"text", "diarized_text", "segments"}` | Audio → Text mit Sprechern |
| `/v1/process` | POST | `file` (multipart), `model` (form), `diarize` (form) | `{"text", "diarized_text", "structured_text", "summary"}` | Volle Pipeline |
| `/v1/jobs` | POST/GET | `file` (multipart), `job_type` (form) | `{"id", "status", "job_type", ...}` | Async Job-Verwaltung |
| `/v1/jobs/{id}` | GET | — | Job-Ergebnis (inkl. Versionen) | Job-Detail |

### S2: ML-Service (FastAPI, Port 8091)

Eigenständiger Microservice (`services/ml/`) mit allen ML-Abhängigkeiten
(torch, pyannote.audio, faster-whisper). Wird von stt-server per HTTP aufgerufen.

| Endpoint | Methode | Request | Response | Beschreibung |
|----------|---------|---------|----------|--------------|
| `/v1/transcribe` | POST | `file` (multipart), `model` (form) | `{"text": "..."}` | Transkription via faster-whisper |
| `/v1/diarize` | POST | `file` (multipart), `model` (form) | `{"text", "diarized_text", "segments"}` | Diarization via pyannote + whisper |
| `/health` | GET | — | `{"status": "ok"}` | Health-Check |

### S3: LLM-Service (Ollama, Port 11434)

Ollama stellt eine OpenAI-kompatible API bereit. Das STT-System nutzt ausschließlich
den `/v1/chat/completions`-Endpunkt. Ollama bietet zusätzlich eine native API (`/api/chat`),
die jedoch nicht verwendet wird.

| Endpoint | Methode | Request | Response | Nutzung |
|----------|---------|---------|----------|---------|
| `/v1/chat/completions` | POST | `{"model", "messages": [{"role", "content"}]}` | `{"choices": [{"message": {"content"}}]}` | Strukturierung & Zusammenfassung (`summarize.py`) |
| `/api/tags` | GET | — | `{"models": [...]}` | Health-Check (k8s readiness/liveness Probe) |

### S4: HuggingFace Hub (extern, einmalig)

| Aktion | Protokoll | Beschreibung |
|--------|-----------|--------------|
| Modell-Download | HTTPS | pyannote/speaker-diarization-3.1, einmalig bei Erststart |
| Authentifizierung | Bearer Token | `HF_STT_TOKEN` als Authorization-Header |

## Datenfluss

```txt
Audio (.wav)
    │
    ▼
┌──────────────────────────────────────────────────────────────────┐
│                     stt-server (Django/DRF)                      │
│                     Orchestrierung & API                         │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐   │
│   │                  stt-ml (FastAPI :8091)                   │   │
│   │                                                          │   │
│   │  ┌──────────────────┐    ┌──────────────────┐            │   │
│   │  │  Transkription   │───►│  Diarization     │            │   │
│   │  │  (faster-whisper)│    │  (pyannote.audio)│            │   │
│   │  │                  │    │                  │            │   │
│   │  │  Audio → Text +  │    │  Audio → Speaker │            │   │
│   │  │  Timestamps      │    │  Labels + Text   │            │   │
│   │  └──────────────────┘    └──────────────────┘            │   │
│   └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│   ┌──────────────────────────────────────────┐                   │
│   │              LLM-Service (Ollama)         │                   │
│   │                                          │                   │
│   │  ┌──────────────────┐  ┌──────────────┐  │                   │
│   │  │  Strukturierung  │  │Zusammen-     │  │                   │
│   │  │  Text → Markdown │  │fassung       │  │                   │
│   │  │  mit Überschriften│  │Text → Kompakt│  │                   │
│   │  └──────────────────┘  └──────────────┘  │                   │
│   └──────────────────────────────────────────┘                   │
│                          │                                       │
└──────────────────────────┼───────────────────────────────────────┘
                           ▼
                     Ergebnisdateien
                     ├── result.txt
                     ├── result_sprecher.md
                     ├── result_struktur.md
                     └── result_zusammenfassung.md
```

## Infrastruktur & Netzwerk

### Übersicht

```txt
┌─────────────────────────────────────────────────────────────────────────┐
│  Entwicklungsrechner (lokales Netz)                                    │
│                                                                       │
│  ┌───────────────────────────────────┐                                 │
│  │  Docker-Compose (production)      │                                 │
│  │                                   │                                 │
│  │  stt-server ─── stt-ml            │    ┌──────────────────────────┐ │
│  │       │         stt-worker        │    │  k3s-Cluster             │ │
│  │       │         db (postgres)     │    │  192.168.178.80          │ │
│  │       │                           │    │                          │ │
│  │       │  LLM_BASE_URL             │    │  MetalLB: .200 (80/443) │ │
│  │       └──────────────────────────────►  │  └─ ingress-nginx       │ │
│  │          http://ollama.stt.local   │    │     ├─ ollama.stt.local │ │
│  │          (extra_hosts → .200)      │    │     ├─ stt.local        │ │
│  │                                   │    │     └─ minio.stt.local  │ │
│  └───────────────────────────────────┘    │                          │ │
│                                           │  Namespace: stt          │ │
│  /etc/hosts:                              │  ├─ ollama (ClusterIP)   │ │
│  192.168.178.200  ollama.stt.local        │  ├─ postgres (ClusterIP) │ │
│  192.168.178.200  stt.local               │  └─ minio (ClusterIP)   │ │
│  192.168.178.200  minio.stt.local         └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Netzwerk-Pfad: Docker-Container → Ollama

```txt
stt-server Container
  │  DNS: ollama.stt.local → 192.168.178.200 (via extra_hosts in docker-compose.yml)
  ▼
MetalLB LoadBalancer (192.168.178.200:80)
  │  L2-Advertisement via ARP im LAN
  │  IP-Pool: 192.168.178.200-210 (konfiguriert in eRechnung-Projekt)
  ▼
ingress-nginx Controller (Namespace ingress-nginx)
  │  Routing nach Host-Header: ollama.stt.local
  │  NetworkPolicy: allow-ingress-egress erlaubt Egress zu stt:11434
  ▼
Ollama Service (ClusterIP 10.43.x.x:11434, Namespace stt)
  │
  ▼
Ollama Pod → /v1/chat/completions → Mistral-Modell (7.2B, in PVC ollama-data)
```

### Nicht-triviale Abhängigkeiten

| Abhängigkeit | Konfiguration | Datei | Warum nötig |
|---|---|---|---|
| **DNS im Container** | `extra_hosts: ollama.stt.local:192.168.178.200` | `docker-compose.yml` (stt-server, stt-worker) | Docker-Container erben nicht `/etc/hosts` des Hosts |
| **Egress-NetworkPolicy** | Ingress-nginx braucht Egress-Regel für `stt`-Namespace | `k8s/base/networkpolicy-ingress-egress-stt.yaml` | Ohne Policy → 502 Bad Gateway (Connection refused) |
| **MetalLB IP-Pool** | `192.168.178.200-210` im LAN reserviert | `eRechnung/.../metallb-lan-config.yaml` | LoadBalancer-IP muss außerhalb des DHCP-Bereichs liegen |
| **Modell-Persistenz** | PVC `ollama-data` (20Gi, local-path) | `k8s/base/ollama.yaml` | Modell (~4 GB) überlebt Pod-Neustarts |
| **Ingress-Timeout** | `proxy-read/send-timeout: 3600` | `k8s/base/ollama.yaml` (Annotations) | LLM-Inferenz kann bei CPU-only mehrere Minuten dauern |
| **Port-Mapping** | Ollama intern :11434, Ingress extern :80 | Ingress + ClusterIP Service | Clients sprechen Port 80 an, nicht 11434 |

### Konfigurationsreferenz

| Variable | Docker-Compose | k8s (values-k3s.yaml) | Bedeutung |
|---|---|---|---|
| `LLM_BASE_URL` | `http://ollama.stt.local` (via Ingress) | `http://ollama:11434` (ClusterIP direkt) | Ollama-Endpunkt |
| `LLM_MODEL` | `mistral` | `mistral` | Ollama-Modellname |
| `LLM_TIMEOUT` | `3600` (in .env) | — (Code-Default: 120s) | HTTP-Timeout für LLM-Anfragen |
