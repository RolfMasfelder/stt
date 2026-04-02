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
| `stt-server` | production | FastAPI-Server, Port 8001 | Eigenes Dockerfile |
| `stt-cli` | cli | CLI-Tool, nutzt STT_SERVER_URL | Eigenes Dockerfile |
| `stt-dev` | dev | Entwicklungsshell mit bash | Eigenes Dockerfile |
| `whisper-server` | whisper-remote | Optionaler Whisper-Server | `fedirz/faster-whisper-server:latest-cpu` |
| `ollama` | ollama | Ollama LLM-Inferenz-Server | `ollama/ollama:latest` |
