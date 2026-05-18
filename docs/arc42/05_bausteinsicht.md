# 5. Bausteinsicht

## Ebene 1 – Gesamtsystem

```
┌─────────────────────────────────────────────────────────┐
│                      stt (Python-Paket)                 │
│                                                         │
│  ┌──────────┐  ┌────────────┐  ┌───────────────────┐   │
│  │ __main__ │  │  server.py │  │    client.py      │   │
│  │ (CLI)    │  │  (FastAPI) │  │  (HTTP-Client)    │   │
│  └────┬─────┘  └─────┬──────┘  └───────────────────┘   │
│       │               │                                  │
│       ▼               ▼                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Verarbeitungsmodule                  │   │
│  │                                                   │   │
│  │  ┌──────────────┐ ┌────────────┐ ┌────────────┐  │   │
│  │  │ transcribe.py│ │ diarize.py │ │summarize.py│  │   │
│  │  └──────────────┘ └────────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────────┐  ┌──────────────────┐                 │
│  │  config.py   │  │ logging_setup.py │                 │
│  └──────────────┘  └──────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

## Ebene 2 – Modulbeschreibungen

### config.py

- Zentrale Konfiguration via frozen Dataclasses
- Lädt Umgebungsvariablen aus `.env`
- Klassen: `WhisperConfig`, `DiarizeConfig`, `LLMConfig`, `AppConfig`

### transcribe.py

- Audio-Transkription (lokal oder remote)
- Lokal: faster-whisper `WhisperModel`
- Remote: HTTP POST an faster-whisper-server `/v1/audio/transcriptions`

### diarize.py

- Kombiniert Whisper-Timestamps mit pyannote Speaker-Diarization
- Erzeugt `DiarizedSegment`-Objekte (speaker, start, end, text)
- Normalisiert Sprecher-Labels (SPEAKER_00 → Sprecher 1)

### summarize.py

- LLM-basierte Textverarbeitung via Ollama API (`POST /v1/chat/completions`, OpenAI-kompatibel)
- Funktionen: `summarize_text`, `structure_text`, `diarize_text`, `process_transcript`
- System-Prompts definieren das LLM-Verhalten pro Aufgabe
- Fehlerbehandlung: `SummarizationError` bei Verbindungs-, Timeout- und HTTP-Fehlern

### api/ (Django-App)

- Django/DRF-Anwendung: REST-API, Modelle, Tasks, Migrationen
- Endpoints: `/health`, `/v1/transcribe`, `/v1/diarize`, `/v1/process`, `/v1/jobs/...`
- Empfängt Audio-Dateien als Multipart-Upload
- Orchestriert transcribe/diarize/summarize Module
- Async Job-Queue via django-q2 (Worker-Prozess: `stt-worker`)

### client.py

- HTTP-Client (`STTClient`) für die Server-API
- Methoden: `health()`, `transcribe()`, `diarize()`, `process()`
- Gibt typisierte Ergebnis-Dataclasses zurück

### __main__.py

- CLI-Entry-Point mit argparse
- Erkennt automatisch: lokaler Modus vs. Remote-Server (via `STT_SERVER_URL`)
- Enthält `_run_remote()` für Server-Delegation

## Abhängigkeiten zwischen Modulen

```txt
__main__.py ──► config.py
            ──► client.py (wenn STT_SERVER_URL gesetzt)
            ──► transcribe.py (lokaler Modus)
            ──► diarize.py (lokaler Modus)
            ──► summarize.py (lokaler Modus)

server.py   ──► config.py
            ──► transcribe.py
            ──► diarize.py
            ──► summarize.py

client.py   ──► (keine internen Abhängigkeiten, nur requests)

diarize.py  ──► config.py
            ──► (nutzt intern Whisper für Timestamps)
```
