# arc42 – Architekturdokumentation STT

Dieses Verzeichnis enthält die Architekturdokumentation des STT-Projekts nach dem arc42-Template.

## Struktur

| Datei | arc42-Abschnitt | Inhalt |
|-------|-----------------|--------|
| [01_einfuehrung.md](01_einfuehrung.md) | 1. Einführung und Ziele | Aufgabenstellung, Qualitätsziele, Stakeholder |
| [02_randbedingungen.md](02_randbedingungen.md) | 2. Randbedingungen | Technische und organisatorische Constraints |
| [03_kontextabgrenzung.md](03_kontextabgrenzung.md) | 3. Kontextabgrenzung | Systemkontext und externe Schnittstellen |
| [04_loesungsstrategie.md](04_loesungsstrategie.md) | 4. Lösungsstrategie | Zentrale Entwurfsentscheidungen |
| [05_bausteinsicht.md](05_bausteinsicht.md) | 5. Bausteinsicht | Modulstruktur und Abhängigkeiten |
| [06_laufzeitsicht.md](06_laufzeitsicht.md) | 6. Laufzeitsicht | Ablaufszenarien |
| [07_verteilungssicht.md](07_verteilungssicht.md) | 7. Verteilungssicht | Deployment-Topologie |
| [08_entscheidungen.md](08_entscheidungen.md) | 8. Architekturentscheidungen | ADRs Phase 1 (ADR-01 bis ADR-05) |

## Architecture Decision Records — Phase 2 (Produktausbau)

| ADR | Titel | Status |
|-----|-------|--------|
| [ADR-06](ADR-06_zero_trust.md) | Zero-Trust-Sicherheitsarchitektur | Vorgeschlagen |
| [ADR-07](ADR-07_authentifizierung.md) | Authentifizierung und Autorisierung via OAuth2/OIDC | Vorgeschlagen |
| [ADR-08](ADR-08_verschluesselung.md) | Ende-zu-Ende-Verschlüsselung | Vorgeschlagen |
| [ADR-09](ADR-09_eu_hosting.md) | Deployment-Szenarien und EU-Hosting | Vorgeschlagen |
| [ADR-10](ADR-10_mobile_app.md) | Mobile App Technologiewahl | Vorgeschlagen |
| [ADR-11](ADR-11_storage_backends.md) | Konfigurierbare Storage Backends | Vorgeschlagen |
| [ADR-12](ADR-12_konfiguration_api.md) | Konfigurations-API für Frontend-gesteuerte Einstellungen | Vorgeschlagen |
| [ADR-13](ADR-13_dsgvo_konzept.md) | DSGVO-Konformitätskonzept | Vorgeschlagen |
| [ADR-14](ADR-14_api_security.md) | API-Sicherheit und Härtung | Vorgeschlagen |

### ADR Status-Werte

- **Vorgeschlagen** — Entscheidung dokumentiert, noch nicht abgestimmt
- **Akzeptiert** — Entscheidung abgestimmt und gültig
- **Abgelöst** — Durch neuere ADR ersetzt
- **Verworfen** — Entscheidung zurückgezogen
