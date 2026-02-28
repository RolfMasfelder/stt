# Lokale Meeting-Transkription und Zusammenfassung

Dieses Projekt zeigt eine minimalistische Pipeline:
1. Meeting oder Audio aufnehmen (z. B. WAV-Datei).
2. Transkription mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
3. Zusammenfassung mit einem lokalen LLM über [LM Studio](https://lmstudio.ai/).

## Voraussetzungen
- Linux (getestet mit openSUSE)
- Python 3.12+ (in venv empfohlen)
- LM Studio installiert und laufend (API-URL via `.env` konfigurierbar)

## Installation
```bash
python -m venv --prompt stt venv
source venv/bin/activate
pip install -r requirements.txt
```

## Nutzung
```bash
# Audio-Datei transkribieren
python -m stt meeting.wav

# Mit Zusammenfassung via LM Studio
python -m stt meeting.wav --summarize

# Ausgabe in Datei
python -m stt meeting.wav -o output/transcript.txt

# Via Docker
docker-compose --profile dev up stt-dev
docker-compose exec stt-dev python -m stt audio/meeting.wav
```
