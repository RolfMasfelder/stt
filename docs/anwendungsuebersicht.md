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

| Endpoint | Methode | Request | Response |
|----------|---------|---------|----------|
| `/api/chat` | POST | `{"model", "messages": [{"role", "content"}]}` | `{"message": {"content"}}` |

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
