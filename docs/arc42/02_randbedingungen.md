# 2. Randbedingungen

Siehe [req42/randbedingungen.md](../req42/randbedingungen.md) für die vollständige Liste.

## Zusammenfassung

- **Programmiersprache:** Python 3.12+
- **Plattform:** Linux (openSUSE), Docker
- **ML-Frameworks:** faster-whisper (Transkription), pyannote.audio (Diarization)
- **LLM:** Ollama (Produktion, Docker-Container), OpenAI-kompatible API; LM Studio als optionale Entwicklungs-/Prompt-Tuning-Alternative
- **Kein GPU** auf dem Entwicklungsrechner verfügbar
- **Netzwerk:** Lokales Netz 192.168.178.x, Remote-Server auf .80 (cirrus7-neu)
