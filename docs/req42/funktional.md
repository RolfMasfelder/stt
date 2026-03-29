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

---

## FA-10: Mobile App — Audio-Aufnahme

**Beschreibung:** Eine mobile App ermöglicht es Anwendern, Gespräche direkt über das Mikrofon des Smartphones aufzunehmen.

**Akzeptanzkriterien:**

- Aufnahme über das eingebaute Mikrofon des Geräts
- Start/Stop/Pause-Steuerung der Aufnahme
- Anzeige der Aufnahmedauer und Audio-Pegel
- Lokale Zwischenspeicherung der Aufnahme auf dem Gerät
- Unterstützung gängiger Audio-Formate (WAV, MP3, OGG)

**Status:** Geplant

---

## FA-11: Mobile App — Server-Kommunikation

**Beschreibung:** Die Mobile App sendet aufgenommene Audio-Dateien an den konfigurierten STT-Server und empfängt die Ergebnisse.

**Akzeptanzkriterien:**

- Upload der aufgenommenen Audio-Datei an den Server
- Empfang und Anzeige der Verarbeitungsergebnisse (Transkript, Sprecher, Zusammenfassung)
- Fortschrittsanzeige während der Verarbeitung
- Fehlerbehandlung bei Verbindungsabbrüchen (Retry-Logik)
- Anzeige des Verarbeitungsstatus

**Status:** Geplant

---

## FA-12: Konfigurierbare Server-Verbindung

**Beschreibung:** Alle Clients (Mobile App, CLI) können die Server-Verbindung frei konfigurieren. Keine hart codierten Verbindungseinstellungen.

**Akzeptanzkriterien:**

- Server-URL konfigurierbar (Host, Port, Pfad)
- TLS-Einstellungen konfigurierbar (Zertifikate, CA)
- Authentifizierungsdaten konfigurierbar (Token, Credentials)
- Verbindungstest-Funktion (Connectivity Check gegen `/health`)
- Konfiguration persistiert auf dem Client

**Status:** Geplant

---

## FA-13: Konfigurierbare Ablageorte (Storage Backends)

**Beschreibung:** Verarbeitungsergebnisse können an verschiedene Ablageorte gespeichert werden. Default: direkte Rückgabe an den Client. Optional: Ablage auf einem File-Storage.

**Akzeptanzkriterien:**

- Default-Verhalten: Ergebnisse werden als Response an den Client zurückgegeben
- Konfiguration von alternativen Ablageorten (z. B. S3-kompatibel, WebDAV, SFTP)
- Ablageort-Konfiguration im Frontend erstellbar und an Server übertragbar
- Server speichert Ergebnisse am konfigurierten Ablageort
- Mehrere Ablageorte parallel konfigurierbar

**Status:** Geplant

---

## FA-14: Storage-Konfiguration Testfunktion

**Beschreibung:** Der Server bietet Testfunktionen, mit denen ein konfigurierter Ablageort validiert werden kann.

**Akzeptanzkriterien:**

- API-Endpoint zum Testen einer Storage-Konfiguration
- Prüfung: Verbindung herstellbar
- Prüfung: Schreibrechte vorhanden
- Prüfung: Leserechte vorhanden (für späteres Abrufen)
- Feedback an das Frontend mit Erfolg/Fehler-Details

**Status:** Geplant

---

## FA-15: Authentifizierung

**Beschreibung:** Nur authentifizierte Anwender dürfen auf die API und die Verarbeitungsfunktionen zugreifen.

**Akzeptanzkriterien:**

- Authentifizierung über standardisiertes Protokoll (OAuth2 / OIDC)
- Token-basierter Zugriff (Bearer Token)
- Token-Refresh ohne erneute Anmeldung
- Abgelaufene Tokens werden abgewiesen (HTTP 401)
- Registrierung / Benutzerverwaltung (Admin-Funktion)

**Status:** Geplant

---

## FA-16: Audit-Logging

**Beschreibung:** Alle Zugriffe und Datenverarbeitungen werden protokolliert (DSGVO Art. 30 — Verarbeitungsverzeichnis).

**Akzeptanzkriterien:**

- Protokollierung: Wer hat wann welche Daten verarbeitet
- Protokollierung: Wer hat wann auf welche Ergebnisse zugegriffen
- Keine Speicherung von Audio- oder Textinhalten im Audit-Log
- Audit-Logs manipulationssicher gespeichert
- Aufbewahrungsfrist konfigurierbar

**Status:** Geplant

---

## FA-17: Recht auf Löschung (DSGVO Art. 17)

**Beschreibung:** Anwender können ihre verarbeiteten Daten (Audio, Transkripte, Ergebnisse) vollständig löschen lassen.

**Akzeptanzkriterien:**

- API-Endpoint zur Löschung aller Daten eines Verarbeitungsauftrags
- Löschung umfasst: Audio-Datei, Transkript, Sprecherzuordnung, Strukturierung, Zusammenfassung
- Löschung auf allen konfigurierten Ablageorten
- Bestätigung der Löschung an den Aufrufer
- Löschvorgang im Audit-Log protokolliert (ohne Inhaltsdaten)

**Status:** Geplant

---

## FA-18: Sichtkontrolle und Korrektur von Zwischenergebnissen

**Beschreibung:** Die Verarbeitungspipeline (Transkription → Sprechererkennung → Strukturierung → Zusammenfassung) ist fehlerbehaftet. Anwender müssen Zwischenergebnisse prüfen, manuell korrigieren und die Pipeline ab dem korrigierten Schritt fortsetzen können.

**Akzeptanzkriterien:**

- Zwischenergebnisse (_sprecher.md, _struktur.md, _zusammenfassung.md) sind einzeln abrufbar und editierbar
- Korrigierte Zwischenergebnisse können als Eingabe für den nächsten Verarbeitungsschritt verwendet werden
- Die Pipeline kann ab einem beliebigen Zwischenschritt neu gestartet werden (z. B. korrigiertes Transkript → erneute Strukturierung → erneute Zusammenfassung)
- Korrektur-Workflow im Frontend (Mobile App und CLI) unterstützt
- Bestehendes CLI-Verhalten (`--skip --text-file`) deckt den Korrektur-Workflow für Text-Eingaben bereits ab

**Vorhandene Grundlage:** Der Parameterbestand (`--skip`, `--text-file`, `--diarize`, `--process`, `--summarize`) ermöglicht bereits heute die Wiederaufnahme der Pipeline ab einem korrigierten Text. Für den Produktausbau muss dies:

1. Im Frontend (App) als expliziter Workflow abgebildet werden (Ergebnis anzeigen → korrigieren → weiterverarbeiten)
2. Über die REST-API als einzelne Verarbeitungsschritte aufrufbar sein (nicht nur als Gesamtpipeline)
3. Versionierung der Zwischenergebnisse (Original vs. korrigierte Fassung) ermöglichen

**Status:** Teilweise umgesetzt (CLI), Geplant (API, Frontend)

---

## FA-19: Asynchrone Job-Verarbeitung mit Status-Abfrage

**Beschreibung:** Audio-Verarbeitung (Transkription, Diarization, Summarization) ist langläufig (Sekunden bis Minuten). Clients müssen Jobs einreichen und deren Status asynchron abfragen können, um bei Verbindungsabbrüchen das Ergebnis später abzuholen.

**Akzeptanzkriterien:**

- Audio-Upload erzeugt einen Job mit eindeutiger ID und gibt diese sofort zurück
- Job-Status ist über `GET /api/v1/jobs/{id}` abrufbar (pending, running, completed, failed)
- Ergebnis ist nach Abschluss über den Job-Endpoint abrufbar
- Jobs werden über django-q2 als Task-Queue verarbeitet (ADR-15)
- Fehlgeschlagene Jobs enthalten eine Fehlerbeschreibung im Status
- Jobs werden nach konfigurierbarer Aufbewahrungsfrist automatisch gelöscht (siehe ADR-13)

**Status:** Geplant
