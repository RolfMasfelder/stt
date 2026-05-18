# 4. Lösungsstrategie

## Zentrale Entwurfsentscheidungen

| Entscheidung | Begründung |
|-------------|------------|
| Python als Sprache | Dominantes Ökosystem für ML/Audio-Processing, alle Bibliotheken nativ verfügbar |
| Client/Server-Split | Trennung von schwerem Processing (Server mit GPU-Option) und leichtgewichtigem CLI (lokaler Rechner) |
| FastAPI als Server-Framework | Asynchron, automatische OpenAPI-Dokumentation, gute Performance |
| Konfiguration via Umgebungsvariablen | Docker-freundlich, keine Konfigurationsdateien im Container nötig |
| Frozen Dataclasses für Config | Immutable Konfiguration verhindert versehentliche Änderungen zur Laufzeit |
| OpenAI-kompatible APIs | faster-whisper-server und Ollama nutzen beide das OpenAI-Format — einheitliches Interface. Wechsel des LLM-Backends ohne Code-Änderung möglich. |
| Modularer Pipeline-Aufbau | Jeder Schritt (transcribe, diarize, summarize) unabhängig nutzbar und testbar |

## Technologieauswahl

| Komponente | Technologie | Alternativen (verworfen) |
|------------|-------------|--------------------------|
| Transkription | faster-whisper | OpenAI Whisper (langsamer), whisper.cpp (weniger Python-Integration) |
| Diarization | pyannote.audio | Textbasierte Heuristik (ungenau), NeMo (komplexer), Resemblyzer (kein Diarization-Pipeline) |
| LLM | Ollama (Produktion) | LM Studio (Dev-Alternative, OpenAI-kompatibel), llama.cpp direkt (weniger komfortabel) |
| Server | Django/DRF (stt-server) + FastAPI (stt-ml) | Flask (kein async), reines FastAPI (kein ORM/Admin) |
