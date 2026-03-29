# ADR-06: Zero-Trust-Sicherheitsarchitektur

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** QA-6, Z-10

## Kontext

Das bisherige System läuft ausschließlich im lokalen Netzwerk (192.168.178.x) und vertraut implizit allen Clients. Für den Produktausbau soll der Server auch bei einem Internet-Provider betrieben werden können. Mobile Clients kommunizieren über das Internet. Ein perimeterbasierten Sicherheitsmodell ("innerhalb des LANs ist alles vertrauenswürdig") ist nicht mehr tragfähig.

## Entscheidung

Das Produkt folgt dem Zero-Trust-Prinzip:

1. **Kein implizites Vertrauen** — Jeder Request wird authentifiziert und autorisiert, unabhängig vom Netzwerkstandort
2. **Verschlüsselung überall** — TLS 1.3 für alle Verbindungen, auch intern
3. **Minimale Berechtigungen** — Jeder Client/Nutzer erhält nur die erforderlichen Rechte
4. **Kurzlebige Credentials** — Keine Langzeit-API-Keys, stattdessen kurzlebige Tokens mit Refresh
5. **Verifizierung auf jeder Ebene** — Server vertraut keinem Client ohne Nachweis
6. **Audit aller Zugriffe** — Lückenlose Protokollierung

## Begründung

- Server kann bei Internet-Providern laufen → öffentlich erreichbar
- Mobile Clients verbinden sich über unbekannte Netzwerke
- DSGVO verlangt angemessene technische Schutzmaßnahmen (Art. 32)
- Zero-Trust ist der aktuelle Industriestandard für neue Produkte

## Konsequenzen

- Authentifizierung muss für jeden API-Endpoint implementiert werden
- TLS-Terminierung erforderlich (Reverse-Proxy oder direkt in der App)
- Token-Management auf Client- und Serverseite
- Höherer Implementierungsaufwand, aber notwendig für Produktbetrieb
- Health-Endpoint `/health` kann ohne Auth erreichbar bleiben (kein sensibles Datum)
