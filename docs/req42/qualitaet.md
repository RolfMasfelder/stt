# Qualitätsanforderungen

## Bestehend (Phase 1)

## QA-1: Datenschutz / Datensouveränität

**Priorität:** Hoch

Alle Verarbeitung findet im lokalen Netzwerk statt. Keine Audio- oder Textdaten verlassen das eigene Netz. Einzige externe Abhängigkeit: einmaliger Download der pyannote-Modelle von HuggingFace.

---

## QA-2: Betreibbarkeit

**Priorität:** Mittel

- Deployment via Docker Compose mit einem Befehl
- Konfiguration ausschließlich über Umgebungsvariablen / `.env`
- Health-Check-Endpoint für Monitoring

---

## QA-3: Testbarkeit

**Priorität:** Mittel

- Alle Module mit Unit-Tests abgedeckt
- Integration-Tests für CLI und Server-Endpoints
- Tests lauffähig ohne externe Dienste (vollständig gemockt)

---

## QA-4: Erweiterbarkeit

**Priorität:** Niedrig → **Hoch** (Produktausbau)

- Modularer Aufbau (transcribe, diarize, summarize unabhängig nutzbar)
- Konfiguration über Dataclasses, erweiterbar ohne Codeänderungen
- REST-API ermöglicht alternative Clients
- Storage-Backend-Abstraktion für austauschbare Ablageorte

---

## QA-5: Benutzbarkeit

**Priorität:** Mittel

- Einfache CLI mit wenigen, kombinierbaren Flags
- Sinnvolle Defaults (Modell, Timeouts, Pfade)
- Deutsche Ausgaben für Zusammenfassungen und Strukturierung

---

## Neu (Phase 2 — Produktausbau)

## QA-6: Zero-Trust-Sicherheit

**Priorität:** Hoch

- Kein implizites Vertrauen — jeder Zugriff wird authentifiziert und autorisiert
- Alle Netzwerkkommunikation über TLS 1.3 (verschlüsselt)
- Minimale Berechtigungen (Principle of Least Privilege)
- Keine Langzeit-Tokens — kurzlebige Tokens mit Refresh-Mechanismus
- API-Rate-Limiting gegen Missbrauch

---

## QA-7: DSGVO-Konformität

**Priorität:** Hoch

- Datenminimierung: nur erforderliche Daten werden erhoben
- Zweckbindung: Daten werden nur für den angegebenen Zweck verarbeitet
- Speicherbegrenzung: konfigurierbare Aufbewahrungsfristen
- Recht auf Löschung: vollständige Löschung auf Anfrage
- Recht auf Auskunft: Export der eigenen Daten ermöglichen
- Verarbeitungsverzeichnis (Art. 30): Audit-Logging aller Verarbeitungen
- Auftragsverarbeitung (Art. 28): bei externem Hosting Vertrag erforderlich

---

## QA-8: Verschlüsselung

**Priorität:** Hoch

- **Transport:** TLS 1.3 für alle Client-Server-Kommunikation
- **Speicherung (at rest):** Verschlüsselung aller gespeicherten Audio- und Textdaten
- **Schlüsselverwaltung:** Sichere Verwaltung von Verschlüsselungsschlüsseln
- **Keine Klartext-Speicherung** von Credentials/Tokens auf dem Client

---

## QA-9: Europäische Datensouveränität

**Priorität:** Hoch

- Ausschließlich europäische Hosting-Anbieter
- Datenverarbeitung und -speicherung innerhalb der EU
- Kein Datentransfer in Drittstaaten
- Anbieter unterliegen europäischem Recht

---

## QA-10: Verfügbarkeit und Resilienz

**Priorität:** Mittel

- Graceful Degradation bei Teilausfällen (z. B. Storage nicht erreichbar)
- Retry-Logik für transiente Fehler
- Health-Checks für alle abhängigen Dienste
- Client-seitige Offline-Fähigkeit (Aufnahme funktioniert ohne Server)

---

## QA-11: API-Sicherheit (Best Practice)

**Priorität:** Hoch

- Input-Validierung aller API-Parameter (OWASP)
- Security-Header (HSTS, Content-Security-Policy, X-Content-Type-Options)
- CORS-Policy für Mobile-App-Zugriff
- Request-Size-Limits für Uploads
- Schutz gegen OWASP Top 10
