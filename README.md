# Lokale Meeting-Transkription und Zusammenfassung

Dieses Projekt zeigt eine minimalistische Pipeline:

1. Meeting oder Audio aufnehmen (z. B. WAV-Datei).
2. Transkription mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
3. Sprechererkennung mit [pyannote.audio](https://github.com/pyannote/pyannote-audio) (direkt auf Audio).
4. Zusammenfassung mit einem lokalen LLM über [Ollama](https://ollama.com/).

## Architektur

Drei-Service-Architektur. Der Django-Server (`stt-server`) koordiniert die Verarbeitung
und delegiert ML-Arbeit an spezialisierte Dienste:

```txt
Workstation (Entwicklung)           cirrus7-neu — 192.168.178.80
─────────────────────────           ──────────────────────────────────────
stt-cli (CLI/Client)                Docker Compose (Profile: production)
  └── client.py                     ┌──────────────────────────────────────┐
      POST /v1/... ──────────────►  │  caddy (:443/80)                     │
      (HTTPS via Caddy)             │    └─► stt-server (:8090)            │
      ◄── JSON Response             │          ├─► stt-ml (:8091)          │
                                    │          │     ├── faster-whisper     │
                                    │          │     └── pyannote.audio     │
                                    │          ├─► stt-ollama (:11434)      │
                                    │          └─► db (postgres:5432)       │
                                    └──────────────────────────────────────┘

                                    k3s Cluster (cirrus7-neu + cirrus7)
                                    ┌──────────────────────────────────────┐
                                    │  ingress-nginx → stt-server          │
                                    │  stt-server → stt-ml (ClusterIP)     │
                                    │  stt-server → ollama (ClusterIP)     │
                                    │  stt-server → postgres (ClusterIP)   │
                                    │  stt-server → minio (ClusterIP)      │
                                    └──────────────────────────────────────┘
```

Beide Deployment-Varianten (Docker Compose und k3s) sind **unabhängig** voneinander
konfiguriert und lauffähig. Docker Compose bringt Ollama als eigenen Container mit
(`stt-ollama`); k3s nutzt einen eigenen Ollama-Pod im Namespace `stt`.

- **`stt-server`**: Django/DRF auf Port 8090. REST-API, Orchestrierung, async Jobs.
- **`stt-ml`**: FastAPI-Microservice auf Port 8091. Führt faster-whisper und pyannote.audio aus.
- **`stt-ollama`/`ollama`**: LLM-Inferenz (Ollama) auf Port 11434. Strukturierung und Zusammenfassung.
- **`stt-cli`**: CLI-Tool. Sendet Audio-Dateien an `stt-server` und zeigt/speichert Ergebnisse.

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

Das Dockerfile nutzt einen Multi-Stage-Build:

- **`production`** — schlankes Image ohne Test-Tools (pytest, ruff, bandit)
- **`dev`** — enthält zusätzlich alle Dev/Test-Dependencies

| Profil | Service | Dockerfile-Target | Zweck |
|--------|---------|-------------------|-------|
| `production` | `stt-server` | `production` | Django + Gunicorn |
| `production` | `stt-worker` | `production` | django-q2 Task-Worker |
| `production` | `db` | — (postgres:17) | PostgreSQL-Datenbank |
| `production` | `caddy` | — (caddy:2) | Reverse-Proxy + TLS |
| `production` | `stt-ml` | — (eigenes) | ML-Service: Transkription + Diarization |
| `production` | `ollama` | — (ollama:0.24.0) | LLM-Inferenz (eigenständig, nicht k3s) |
| `test` | `stt-test` | `dev` | pytest-Runner |
| `test` | `db` | — (postgres:17) | PostgreSQL für Tests |
| `cli` | `stt-cli` | `dev` | CLI-Tool |
| `whisper-remote` | `whisper-server` | — (faster-whisper) | Alternativer Whisper-Server |
| `mobile` | `flutter` | — (eigenes) | Flutter-Entwicklung |

```bash
# Alle Container bauen
./scripts/build-containers.sh

# Produktion starten
docker compose --profile production up -d

# Tests ausführen
docker compose run --rm stt-test

# CLI nutzen
docker compose --profile cli run --rm stt-cli python -m stt data/audio/meeting.wav --diarize --process -o data/output/x.txt
# oder auch mit expliziten Umgebungsvariablen (z.B. für caddy ohne Zertifikatsprüfung)
# stt-server auf 'anderem' Rechner
STT_SERVER_URL=http://192.168.178.80:8090 \
OAUTH2_TOKEN_URL=http://192.168.178.80:8090/o/token/ \
REQUESTS_CA_BUNDLE= \
docker compose --profile cli run --rm stt-cli python -m stt data/audio/passwoerter_raus_aus_USCloud.wav --diarize --process -o data/output/x.txt

# voher, um certificate von caddy zu bekommen (falls caddy mit TLS läuft und self-signed Zertifikate nutzt)
ssh rolf@192.168.178.80 "cd workspace/stt && docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt -" | tar xf - -O > ./caddy-root.crt
# bis hierher muss nur einmal gemacht werden

# dann mit certifikat arbeiten
STT_SERVER_URL=https://192.168.178.80 \
OAUTH2_TOKEN_URL=https://192.168.178.80/o/token/ \
REQUESTS_CA_BUNDLE=/app/caddy-root.crt \
docker compose --profile cli run --rm stt-cli python -m stt data/audio/passwoerter_raus_aus_USCloud.wav --diarize --process -o data/output/x.txt
```
