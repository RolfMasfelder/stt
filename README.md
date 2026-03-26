# Lokale Meeting-Transkription und Zusammenfassung

Dieses Projekt zeigt eine minimalistische Pipeline:

1. Meeting oder Audio aufnehmen (z. B. WAV-Datei).
2. Transkription mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
3. Sprechererkennung mit [pyannote.audio](https://github.com/pyannote/pyannote-audio) (direkt auf Audio).
4. Zusammenfassung mit einem lokalen LLM über [LM Studio](https://lmstudio.ai/).

## Architektur

```txt
Lokaler Rechner                     Remote-Rechner 192.168.178.80
──────────────                      ─────────────────────────────
python -m stt meeting.wav           Docker: stt-server (:8001)
  └── client.py                       └── server.py (FastAPI)
      POST /v1/process ──────────►        ├── faster-whisper (Transkription)
      (Audio-Datei)                       ├── pyannote.audio (Diarization)
                                          └──► LM Studio :1234 (Zusammenfassung)
      ◄── JSON Response ─────────
  └── Anzeige / Speicherung
```

Das Projekt besteht aus zwei Varianten in einer `docker-compose.yml`:

- **`stt-server`** (Remote): FastAPI-Server auf Port 8001. Empfängt Audio-Dateien
  via REST-API, führt Transkription, Sprechererkennung und Zusammenfassung durch.
  Kommuniziert mit LM Studio auf dem gleichen Host.
- **`stt-cli`** (Lokal): CLI-Tool. Sendet Audio-Dateien an den Remote-Server und
  zeigt/speichert die Ergebnisse. Keine lokale Whisper- oder pyannote-Installation nötig.

Die API-Schnittstelle ist in [`openapi.json`](openapi.json) definiert.

## Voraussetzungen

- Linux (getestet mit openSUSE)
- Python 3.12+ (in venv empfohlen)
- LM Studio installiert und laufend auf dem Remote-Rechner
- HuggingFace-Token für pyannote-Modelle (`HF_STT_TOKEN` in `.env`)

## Installation

```bash
python -m venv --prompt stt venv
source venv/bin/activate
pip install -r requirements.txt
```

## Nutzung

### CLI mit Remote-Server (empfohlen)

```bash
# Audio-Datei transkribieren (via Remote-Server)
python -m stt meeting.wav

# Mit audio-basierter Sprechererkennung
python -m stt meeting.wav --diarize

# Volle Pipeline: Sprechererkennung + Strukturierung + Zusammenfassung
python -m stt meeting.wav --diarize --process -o data/output/result.txt

# Nur Zusammenfassung (ohne Sprechererkennung)
python -m stt meeting.wav --summarize
```

### Lokale Verarbeitung (ohne Server)

```bash
# Ausgabe in Datei
python -m stt meeting.wav -o data/output/transcript.txt

# LLM-Verarbeitung auf bestehendem Text (kein Audio nötig)
python -m stt --skip --text-file data/output/transcript.txt --diarize -o data/output/result.txt
python -m stt --skip --text-file data/output/transcript.txt --process --diarize -o data/output/result.txt
python -m stt --skip --text-file data/output/transcript.txt --summarize -o data/output/result.txt
```

Hinweis: `--diarize` mit `--skip` verwendet LLM-basierte Sprechererkennung (Heuristik),
da ohne Audiodatei keine audio-basierte Diarization möglich ist.

### Docker

```bash
# Remote: Server starten
docker compose --profile server up -d stt-server

# Lokal via CLI
docker compose --profile cli run --rm stt-cli python -m stt meeting.wav --diarize --process
```
