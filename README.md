# Lokale Meeting-Transkription und Zusammenfassung

Dieses Projekt zeigt eine minimalistische Pipeline:
1. Meeting oder Audio aufnehmen (z. B. WAV-Datei).
2. Transkription mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
3. Sprechererkennung mit [pyannote.audio](https://github.com/pyannote/pyannote-audio) (direkt auf Audio).
4. Zusammenfassung mit einem lokalen LLM über [LM Studio](https://lmstudio.ai/).

## Voraussetzungen
- Linux (getestet mit openSUSE)
- Python 3.12+ (in venv empfohlen)
- LM Studio installiert und laufend (API-URL via `.env` konfigurierbar)
- HuggingFace-Token für pyannote-Modelle (`HF_STT_TOKEN` in `.env`)

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

# Mit audio-basierter Sprechererkennung (benötigt HF_STT_TOKEN in .env)
python -m stt meeting.wav --diarize

# Volle Pipeline: Sprechererkennung + Strukturierung + Zusammenfassung
python -m stt meeting.wav --diarize --process -o output/result.txt

# Mit Zusammenfassung via LM Studio (ohne Sprechererkennung)
python -m stt meeting.wav --summarize

# Ausgabe in Datei
python -m stt meeting.wav -o output/transcript.txt

# Überspringen von SpeechToText (nur LLM-Verarbeitung auf bestehendem Text)
python -m stt --skip --text-file output/transcript.txt --diarize -o output/result.txt
python -m stt --skip --text-file output/transcript.txt --process --diarize -o output/result.txt
python -m stt --skip --text-file output/transcript.txt --summarize -o output/result.txt
```

Hinweis: `--diarize` mit `--skip` verwendet LLM-basierte Sprechererkennung (Heuristik),
da ohne Audiodatei keine audio-basierte Diarization möglich ist.

# Via Docker
docker compose --profile dev up stt-dev
docker compose exec stt-dev python -m stt audio/meeting.wav
```
