# Funktionale Anforderungen

## FA-1: Audio-Transkription

**Beschreibung:** Das System transkribiert Audio-Dateien (WAV, MP3 etc.) zu Text.

**Akzeptanzkriterien:**

- Unterstützung lokaler Transkription via faster-whisper
- Unterstützung remote Transkription via faster-whisper-server (OpenAI-kompatible API)
- Automatische Spracherkennung
- Konfigurierbare Modellgröße (tiny, base, small, medium, large)

**Status:** Umgesetzt (`src/stt/transcribe.py`)

---

## FA-2: Audio-basierte Sprechererkennung

**Beschreibung:** Das System erkennt verschiedene Sprecher in einer Audio-Aufnahme und ordnet Textabschnitte den jeweiligen Sprechern zu.

**Akzeptanzkriterien:**

- Kombination von Whisper-Timestamps mit pyannote.audio Speaker-Diarization
- Automatische Erkennung der Anzahl der Sprecher
- Konsistente Sprecher-Labels (Sprecher 1, Sprecher 2, ...)
- Zusammenfassung aufeinanderfolgender Segmente desselben Sprechers

**Status:** Umgesetzt (`src/stt/diarize.py`)

---

## FA-3: LLM-basierte Sprechererkennung (Fallback)

**Beschreibung:** Wenn keine Audio-Datei vorliegt, identifiziert das System Sprecher anhand von Textmerkmalen (Frage-Antwort-Muster, Sprachstil, Themen).

**Akzeptanzkriterien:**

- Funktioniert auf reinem Text (kein Audio nötig)
- Nutzbar mit `--skip --text-file --diarize`
- Verwendet LM Studio als LLM-Backend

**Status:** Umgesetzt (`src/stt/summarize.py`, Funktion `diarize_text`)

---

## FA-4: Textstrukturierung

**Beschreibung:** Das System gliedert ein Transkript in thematische Abschnitte mit Überschriften.

**Akzeptanzkriterien:**

- Automatische Erkennung thematischer Blöcke
- Markdown-Überschriften (## Heading)
- Vollständiger Textinhalt bleibt erhalten

**Status:** Umgesetzt (`src/stt/summarize.py`, Funktion `structure_text`)

---

## FA-5: Zusammenfassung

**Beschreibung:** Das System erstellt eine kompakte Zusammenfassung eines strukturierten Transkripts.

**Akzeptanzkriterien:**

- Maximal 2-3 Sätze pro Abschnitt
- Beibehaltung der Abschnittsstruktur
- Markdown-Ausgabe

**Status:** Umgesetzt (`src/stt/summarize.py`, Funktion `summarize_text`)

---

## FA-6: Volle Pipeline (--process)

**Beschreibung:** Ein einziger Befehl führt die gesamte Verarbeitungskette aus: Transkription → Sprechererkennung → Strukturierung → Zusammenfassung.

**Akzeptanzkriterien:**

- Steuerung über `--process` CLI-Flag
- Optionale Sprechererkennung mit `--diarize`
- Speicherung von Teilergebnissen (_sprecher.md, _struktur.md, _zusammenfassung.md)

**Status:** Umgesetzt (`src/stt/__main__.py`, `src/stt/summarize.py` Funktion `process_transcript`)

---

## FA-7: REST-API (Server-Modus)

**Beschreibung:** Das System bietet eine HTTP-API zur Verarbeitung von Audio-Dateien.

**Akzeptanzkriterien:**

- FastAPI-Server auf konfigurierbarem Port
- Endpoints: `/health`, `/v1/transcribe`, `/v1/diarize`, `/v1/process`
- Multipart-Upload von Audio-Dateien
- JSON-Responses mit Ergebnissen
- API-Definition via OpenAPI-Spezifikation

**Status:** Umgesetzt (`src/stt/server.py`, `openapi.json`)

---

## FA-8: Remote-Client

**Beschreibung:** Das CLI erkennt automatisch, ob ein STT-Server konfiguriert ist und delegiert die Verarbeitung an diesen.

**Akzeptanzkriterien:**

- Konfiguration via `STT_SERVER_URL` Umgebungsvariable
- Gleiches CLI-Interface wie lokaler Modus
- Transparente Umschaltung zwischen lokal und remote

**Status:** Umgesetzt (`src/stt/client.py`, `src/stt/__main__.py`)

---

## FA-9: Text-Eingabe (--skip)

**Beschreibung:** Statt einer Audio-Datei kann ein bereits vorhandenes Transkript als Text-Datei übergeben werden.

**Akzeptanzkriterien:**

- Steuerung über `--skip --text-file <pfad>`
- Kombinierbar mit `--diarize`, `--process`, `--summarize`
- Keine Audio-Verarbeitung nötig

**Status:** Umgesetzt (`src/stt/__main__.py`)
