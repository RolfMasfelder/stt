# Qualitätsanforderungen

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

**Priorität:** Niedrig

- Modularer Aufbau (transcribe, diarize, summarize unabhängig nutzbar)
- Konfiguration über Dataclasses, erweiterbar ohne Codeänderungen
- REST-API ermöglicht alternative Clients

---

## QA-5: Benutzbarkeit

**Priorität:** Mittel

- Einfache CLI mit wenigen, kombinierbaren Flags
- Sinnvolle Defaults (Modell, Timeouts, Pfade)
- Deutsche Ausgaben für Zusammenfassungen und Strukturierung
