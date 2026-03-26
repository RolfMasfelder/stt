# Anwendungsübersicht und Schnittstellen

## Gesamtübersicht

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              STT-System                                        │
│                                                                                 │
│  ┌─────────────────────────┐              ┌─────────────────────────────────┐   │
│  │   Lokaler Rechner       │    HTTP      │   Remote-Server (.80)           │   │
│  │                         │              │                                 │   │
│  │  ┌───────────────────┐  │              │  ┌───────────────────────────┐  │   │
│  │  │  CLI (__main__.py)│  │              │  │  FastAPI (server.py)     │  │   │
│  │  │                   │  │              │  │  :8001                   │  │   │
│  │  │  --diarize        │  │  ┌────────┐  │  │                         │  │   │
│  │  │  --process        │──┼─►│ REST   │──┼─►│  /health          [GET] │  │   │
│  │  │  --summarize      │  │  │ API    │  │  │  /v1/transcribe  [POST] │  │   │
│  │  │  --skip           │◄─┼──│        │◄─┼──│  /v1/diarize     [POST] │  │   │
│  │  │                   │  │  └────────┘  │  │  /v1/process     [POST] │  │   │
│  │  └───────┬───────────┘  │              │  └──────┬──────┬───────────┘  │   │
│  │          │              │              │         │      │              │   │
│  │  ┌───────▼───────────┐  │              │  ┌──────▼──────▼───────────┐  │   │
│  │  │  client.py        │  │              │  │ Verarbeitungsmodule     │  │   │
│  │  │  (STTClient)      │  │              │  │                         │  │   │
│  │  └───────────────────┘  │              │  │ transcribe.py           │  │   │
│  │                         │              │  │ diarize.py              │  │   │
│  │  ┌───────────────────┐  │              │  │ summarize.py            │  │   │
│  │  │  data/            │  │              │  └──────┬──────┬───────────┘  │   │
│  │  │  ├── audio/       │  │              │         │      │              │   │
│  │  │  └── output/      │  │              │         │      │              │   │
│  │  └───────────────────┘  │              │         │      │              │   │
│  └─────────────────────────┘              │  ┌──────▼────┐ │              │   │
│                                           │  │ faster-   │ │              │   │
│                                           │  │ whisper   │ │              │   │
│                                           │  │ (lokal    │ │              │   │
│                                           │  │ od. :8000)│ │              │   │
│                                           │  └───────────┘ │              │   │
│                                           │         ┌──────▼────┐         │   │
│                                           │         │ LM Studio │         │   │
│                                           │         │ :1234     │         │   │
│                                           │         └───────────┘         │   │
│                                           └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Schnittstellen im Detail

### S1: STT Server REST-API (intern, Port 8001)

Definiert in [`openapi.json`](../openapi.json).

| Endpoint | Methode | Request | Response | Beschreibung |
|----------|---------|---------|----------|--------------|
| `/health` | GET | — | `{"status": "ok"}` | Health-Check |
| `/v1/transcribe` | POST | `file` (multipart), `model` (form) | `{"text": "..."}` | Audio → Text |
| `/v1/diarize` | POST | `file` (multipart), `model` (form) | `{"text", "diarized_text", "segments"}` | Audio → Text mit Sprechern |
| `/v1/process` | POST | `file` (multipart), `model` (form), `diarize` (form) | `{"text", "diarized_text", "structured_text", "summary"}` | Volle Pipeline |

### S2: faster-whisper-server (OpenAI-kompatibel, Port 8000)

| Endpoint | Methode | Request | Response |
|----------|---------|---------|----------|
| `/v1/audio/transcriptions` | POST | `file` (multipart), `model`, `response_format` | Text oder JSON mit Segmenten |

### S3: LM Studio (OpenAI-kompatibel, Port 1234)

| Endpoint | Methode | Request | Response |
|----------|---------|---------|----------|
| `/v1/chat/completions` | POST | `{"model", "messages": [{"role", "content"}]}` | `{"choices": [{"message": {"content"}}]}` |

### S4: HuggingFace Hub (extern, einmalig)

| Aktion | Protokoll | Beschreibung |
|--------|-----------|--------------|
| Modell-Download | HTTPS | pyannote/speaker-diarization-3.1, einmalig bei Erststart |
| Authentifizierung | Bearer Token | `HF_STT_TOKEN` als Authorization-Header |

## Datenfluss

```
Audio (.wav)
    │
    ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Transkription   │───►│  Diarization     │───►│  Strukturierung  │
│  (faster-whisper)│    │  (pyannote.audio)│    │  (LM Studio)     │
│                  │    │                  │    │                  │
│  Audio → Text +  │    │  Audio → Speaker │    │  Text → Markdown │
│  Timestamps      │    │  Labels          │    │  mit Überschriften│
└──────────────────┘    └──────────────────┘    └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │  Zusammenfassung │
                                                │  (LM Studio)     │
                                                │                  │
                                                │  Text → Kompakte │
                                                │  Übersicht       │
                                                └──────────────────┘
                                                         │
                                                         ▼
                                                   Ergebnisdateien
                                                   ├── result.txt
                                                   ├── result_sprecher.md
                                                   ├── result_struktur.md
                                                   └── result_zusammenfassung.md
```
