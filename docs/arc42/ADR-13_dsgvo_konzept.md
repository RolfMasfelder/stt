# ADR-13: DSGVO-Konformitätskonzept

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** QA-7, Z-11, RB-22, RB-30–RB-33

## Kontext

Audio-Aufnahmen enthalten personenbezogene Daten (Stimmen sind biometrische Merkmale). Sprechererkennung ordnet diese explizit Personen zu. Das Produkt muss DSGVO-konform betrieben werden können.

## Entscheidung

### Rechtsgrundlage

Die Verarbeitung basiert auf **Einwilligung (Art. 6 Abs. 1 lit. a)** oder **berechtigtem Interesse (Art. 6 Abs. 1 lit. f)** — abhängig vom Einsatzszenario des Betreibers.

### Technische Maßnahmen

| DSGVO-Artikel | Maßnahme | Umsetzung |
|---------------|----------|-----------|
| Art. 5 Abs. 1c | Datenminimierung | Nur erforderliche Daten erheben, temporäre Dateien sofort löschen |
| Art. 5 Abs. 1e | Speicherbegrenzung | Konfigurierbare Aufbewahrungsfristen, automatische Löschung |
| Art. 17 | Recht auf Löschung | API-Endpoint für vollständige Datenlöschung (FA-17) |
| Art. 20 | Datenportabilität | Export aller Daten in gängigem Format (JSON, ZIP) |
| Art. 25 | Privacy by Design | Verschlüsselung, Zero-Trust, Datenminimierung als Default |
| Art. 28 | Auftragsverarbeitung | AV-Vertrag-Template für Betreiber bereitstellen |
| Art. 30 | Verarbeitungsverzeichnis | Automatisches Audit-Logging (FA-16) |
| Art. 32 | Technische Schutzmaßnahmen | Verschlüsselung, Zugangskontrolle, Pseudonymisierung |
| Art. 33/34 | Meldepflicht bei Verletzung | Incident-Response-Prozess dokumentieren |

### Datenfluss und Aufbewahrung

```
Audio-Upload → Verarbeitung → Ergebnis-Rückgabe → Aufbewahrungsfrist → Automatische Löschung
                                   │
                                   ├── Audio: sofort nach Verarbeitung löschen (Default)
                                   ├── Transkript: gem. konfig. Aufbewahrungsfrist
                                   └── Audit-Log: 90 Tage (Default, konfigurierbar)
```

### Pseudonymisierung

- Sprecher werden als "Sprecher 1", "Sprecher 2" etc. identifiziert (bereits umgesetzt)
- Keine automatische Zuordnung zu realen Namen
- Zuordnung zu realen Personen nur durch den Nutzer selbst (clientseitig)

## Begründung

- Audio mit Stimmen fällt unter personenbezogene Daten
- Sprechererkennung (Diarization) kann als biometrische Verarbeitung gelten (Art. 9)
- Privacy by Design (Art. 25) erfordert datenschutzfreundliche Voreinstellungen
- Automatische Löschung reduziert das Risiko bei Datenpannen

## Konsequenzen

- Auto-Delete-Mechanismus für abgelaufene Daten (Cron-Job oder Background-Task)
- Lösch-API (FA-17) muss alle Ablageorte berücksichtigten
- Datenschutzhinweise/Dokumentation für Betreiber bereitstellen
- Ggf. Datenschutz-Folgenabschätzung (DSFA, Art. 35) erforderlich
- AV-Vertrag-Template als Dokument im Projekt bereitstellen

## Offene Fragen

- [ ] Ist eine Datenschutz-Folgenabschätzung (DSFA) erforderlich?
- [ ] Wer ist verantwortliche Stelle — der Betreiber oder der Hersteller?
- [ ] Müssen Aufnahme-Teilnehmer informiert/eingewilligt werden (durch die App)?
- [ ] Wie wird mit Stimmen von Dritten umgegangen, die nicht eingewilligt haben?
