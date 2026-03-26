# Randbedingungen

## Technisch

| ID | Randbedingung | Begründung |
|----|---------------|------------|
| RB-1 | Python 3.12+ | Verwendung moderner Syntax (type unions `X \| None`, etc.) |
| RB-2 | Linux (openSUSE) | Entwicklungs- und Zielplattform |
| RB-3 | Docker / Docker Compose | Container-basiertes Deployment auf Remote-Server |
| RB-4 | faster-whisper | Effiziente lokale Whisper-Implementierung (CTranslate2) |
| RB-5 | pyannote.audio 4.x | State-of-the-art Speaker Diarization, läuft lokal |
| RB-6 | LM Studio | Lokales LLM-Hosting, OpenAI-kompatible API |
| RB-7 | HuggingFace-Token | Erforderlich für pyannote-Modell-Download (einmalig) |
| RB-8 | Kein GPU lokal | CPU-Verarbeitung auf lokalem Rechner, GPU optional auf Server |

## Organisatorisch

| ID | Randbedingung | Begründung |
|----|---------------|------------|
| RB-9 | Einzelentwickler-Projekt | Keine Team-Koordination nötig |
| RB-10 | Keine Cloud-Dienste | Datenschutz — alle Daten bleiben im lokalen Netzwerk |
| RB-11 | Netzwerk: 192.168.178.x | Lokales Heimnetzwerk mit Remote-Server auf .80 |
