# 8. Architekturentscheidungen

## ADR-1: pyannote.audio statt textbasierter Diarization

**Kontext:** Ursprünglich wurde Sprechererkennung rein textbasiert via LLM-Heuristik durchgeführt. Die Ergebnisse waren unzuverlässig bei ähnlichen Sprachstilen.

**Entscheidung:** pyannote.audio 4.x für audio-basierte Speaker Diarization einsetzen.

**Begründung:**

- Nutzt Audiomerkmale (Stimme, Tonhöhe) statt Textheuristik
- State-of-the-art Ergebnisse bei Speaker Diarization
- Läuft lokal, benötigt nur einmaligen Modell-Download
- Kombinierbar mit Whisper-Timestamps für Segment-Zuordnung

**Konsequenzen:**

- HuggingFace-Token erforderlich (akzeptiert Terms of Service)
- Höherer Speicherverbrauch durch pyannote-Modell
- LLM-basierte Diarization bleibt als Fallback für `--skip`-Modus

---

## ADR-2: Client/Server-Split statt monolithischer CLI

**Kontext:** Alle Verarbeitung lief zunächst lokal. Whisper und pyannote sind ressourcenintensiv, der lokale Rechner hat keine GPU.

**Entscheidung:** Aufteilung in leichtgewichtigen CLI-Client (lokal) und Processing-Server (remote, Docker).

**Begründung:**

- Remote-Server kann GPU nutzen
- CLI bleibt schlank, benötigt keine ML-Bibliotheken
- Transparente Umschaltung via `STT_SERVER_URL`
- Gleiche CLI-Flags funktionieren in beiden Modi

**Konsequenzen:**

- FastAPI-Server erforderlich (`server.py`)
- HTTP-Client erforderlich (`client.py`)
- OpenAPI-Spec als Schnittstellenvertrag
- Netzwerklatenz bei Dateitransfer (akzeptabel im LAN)

---

## ADR-3: FastAPI statt Flask

**Kontext:** Auswahl eines Web-Frameworks für die Server-API.

**Entscheidung:** FastAPI verwenden.

**Begründung:**

- Native async-Unterstützung (Upload-Handling)
- Automatische OpenAPI/Swagger-Dokumentation
- Pydantic-Modelle für Request/Response-Validierung
- Form-Parameter-Handling für Multipart-Uploads

**Konsequenzen:**

- uvicorn als ASGI-Server erforderlich
- Pydantic als zusätzliche Abhängigkeit

---

## ADR-4: frozen Dataclasses für Konfiguration

**Kontext:** Konfiguration wird aus Umgebungsvariablen geladen und durchgereicht.

**Entscheidung:** `@dataclass(frozen=True)` für alle Config-Klassen.

**Begründung:**

- Immutability verhindert versehentliche Änderungen
- Konfiguration wird einmal geladen und bleibt konsistent
- `dataclasses.replace()` für explizite Overrides (z. B. CLI-Timeouts)

**Konsequenzen:**

- `replace()` statt direkter Zuweisung bei Übersteuerung

---

## ADR-5: Ollama als LLM-Backend (Produktion)

**Kontext:** Zusammenfassung und Strukturierung benötigen ein LLM. LM Studio war das ursprüngliche Backend (nativ auf dem Remote-Server, kein Docker). Für den Produktionsbetrieb wird ein automatisch startbarer, containerisierter Dienst benötigt.

**Entscheidung:** Ollama als Docker-Container im `production`-Profil. LM Studio bleibt als optionale Entwicklungs- und Prompt-Tuning-Alternative erhalten.

**Begründung:**

- Ollama startet automatisch mit `docker compose --profile production up`
- Kein manuelles Starten eines nativen Prozesses nötig
- OpenAI-kompatible API (`/v1/chat/completions`) — gleiche Schnittstelle wie LM Studio
- Persistentes Volume (`ollama_data`) sichert Modelle über Container-Neustarts
- LM Studio bleibt weiterhin nutzbar durch Änderung von `LLM_BASE_URL` in `.env`

**Konsequenzen:**

- `stt-ollama` Container (`ollama/ollama:0.24.0`) im `production`-Profil
- Einmaliger manueller Schritt: `docker compose exec stt-ollama ollama pull mistral`
- k3s nutzt einen separaten Ollama-Pod im Namespace `stt` (unabhängig von Docker Compose)
- `LLM_BASE_URL=http://stt-ollama:11434` hardcoded für docker-compose (kein extra_hosts mehr)

---

## ADR-6: Verzeichnisstruktur data/audio + data/output

**Kontext:** Audio-Eingabedateien und Ergebnisdateien lagen in separaten Top-Level-Verzeichnissen.

**Entscheidung:** Zusammenfassung unter `data/` mit Unterverzeichnissen `audio/` und `output/`.

**Begründung:**

- Klare Trennung von Code (`src/`) und Daten (`data/`)
- Einfacheres Volume-Mounting in Docker
- Übersichtlichere Projektstruktur

**Konsequenzen:**

- Umgebungsvariablen `AUDIO_INPUT_DIR` und `OUTPUT_DIR` angepasst
- Docker-Volumes zeigen auf `data/audio` und `data/output`
