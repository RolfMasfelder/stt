# 6. Laufzeitsicht

## Szenario 1: Volle Pipeline (Remote, via stt-cli)

```
CLI            STTClient        stt-server (Django)  stt-ml (FastAPI)   Ollama
 |                 |                  |                    |               |
 |--process()----> |                  |                    |               |
 |                 |--POST /v1/process->                   |               |
 |                 |                  |--POST /v1/transcribe->             |
 |                 |                  |<--text-------------|               |
 |                 |                  |--POST /v1/diarize-->               |
 |                 |<--segments-------|                    |               |
 |                 |                  |--POST /v1/chat/completions-------->|
 |                 |                  |<--structured------------------------
 |                 |                  |--POST /v1/chat/completions-------->|
 |                 |                  |<--summary---------------------------
 |                 |<--JSON-----------|                    |               |
 |<--ProcessResult-|                  |                    |               |
```

## Szenario 2: Transkription + Diarization (via stt-ml)

```
stt-server          stt-ml              faster-whisper / pyannote
 |                    |                       |
 |--POST /v1/transcribe->                     |
 |                    |--WhisperModel()------->|
 |                    |<--segments------------|
 |<--{"text": "..."}--|
 |
 |--POST /v1/diarize-->
 |                    |--pyannote.Pipeline()--->|
 |                    |<--speaker segments-----|
 |<--{text, segments}--
```

## Szenario 3: Text-Modus (--skip, kein Audio)

```
CLI              summarize.py         Ollama
 |                    |                    |
 |--read text file    |                    |
 |--process_transcript()-->               |
 |                    |--POST /v1/chat/completions-->|
 |                    |<--structured-------|
 |                    |--POST /v1/chat/completions-->|
 |                    |<--summary----------|
 |<--results----------|
```
