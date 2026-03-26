# 4. Lösungsstrategie

## Zentrale Entwurfsentscheidungen

| Entscheidung | Begründung |
|-------------|------------|
| Python als Sprache | Dominantes Ökosystem für ML/Audio-Processing, alle Bibliotheken nativ verfügbar |
| Client/Server-Split | Trennung von schwerem Processing (Server mit GPU-Option) und leichtgewichtigem CLI (lokaler Rechner) |
| FastAPI als Server-Framework | Asynchron, automatische OpenAPI-Dokumentation, gute Performance |
| Konfiguration via Umgebungsvariablen | Docker-freundlich, keine Konfigurationsdateien im Container nötig |
| Frozen Dataclasses für Config | Immutable Konfiguration verhindert versehentliche Änderungen zur Laufzeit |
| OpenAI-kompatible APIs | faster-whisper-server und LM Studio nutzen beide das OpenAI-Format — einheitliches Interface |
| Modularer Pipeline-Aufbau | Jeder Schritt (transcribe, diarize, summarize) unabhängig nutzbar und testbar |

## Technologieauswahl

| Komponente | Technologie | Alternativen (verworfen) |
|------------|-------------|--------------------------|
| Transkription | faster-whisper | OpenAI Whisper (langsamer), whisper.cpp (weniger Python-Integration) |
| Diarization | pyannote.audio | Textbasierte Heuristik (ungenau), NeMo (komplexer), Resemblyzer (kein Diarization-Pipeline) |
| LLM | LM Studio | Ollama (weniger Model-Management), llama.cpp direkt (weniger komfortabel) |
| Server | FastAPI | Flask (kein async), Django (zu schwergewichtig) |
