# Lokale Meeting-Transkription und Zusammenfassung

Dieses Projekt zeigt eine minimalistische Pipeline:
1. Meeting oder Audio aufnehmen (z. B. WAV-Datei).
2. Transkription mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
3. Zusammenfassung mit einem lokalen LLM über [LM Studio](https://lmstudio.ai/).

## Voraussetzungen
- Linux (getestet mit openSUSE)
- Python 3.12 (in venv empfohlen)
- LM Studio installiert und laufend (API auf `http://cirrus7-neu:1234`)

## Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
