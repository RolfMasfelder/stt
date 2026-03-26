# 3. Kontextabgrenzung

## Fachlicher Kontext

```
                        ┌─────────────────────┐
                        │                     │
  Audio-Datei (.wav) ──►│    STT-System       │──► Transkript (.txt)
                        │                     │──► Sprecherzuordnung (.md)
                        │                     │──► Strukturierung (.md)
                        │                     │──► Zusammenfassung (.md)
                        │                     │
                        └─────────────────────┘
                                ▲
                                │
                          Nutzer (CLI)
```

Der Nutzer übergibt eine Audio-Datei per Kommandozeile. Das System liefert Text-Ergebnisse als Dateien oder auf stdout.

## Technischer Kontext

```
┌──────────────────┐         HTTP/REST          ┌──────────────────────────┐
│  Lokaler Rechner │ ─────────────────────────► │  Remote 192.168.178.80   │
│                  │                             │                          │
│  python -m stt   │  POST /v1/process           │  stt-server (:8001)      │
│  (CLI + Client)  │  ◄── JSON ──────────────── │  ├── FastAPI             │
│                  │                             │  ├── faster-whisper      │
└──────────────────┘                             │  └── pyannote.audio     │
                                                 │                          │
                                                 │  LM Studio (:1234)      │
                                                 │  (nativ, kein Docker)    │
                                                 │                          │
                                                 │  faster-whisper-server   │
                                                 │  (:8000, optional)       │
                                                 └──────────────────────────┘
```

### Externe Schnittstellen

| Schnittstelle | Protokoll | Beschreibung |
|---------------|-----------|--------------|
| STT Server API | HTTP/REST | `/v1/transcribe`, `/v1/diarize`, `/v1/process`, `/health` — definiert in `openapi.json` |
| faster-whisper-server | HTTP/REST | OpenAI-kompatible API `/v1/audio/transcriptions` |
| LM Studio | HTTP/REST | OpenAI-kompatible API `/v1/chat/completions` |
| HuggingFace Hub | HTTPS | Einmaliger Modell-Download für pyannote (nur bei Erststart) |
