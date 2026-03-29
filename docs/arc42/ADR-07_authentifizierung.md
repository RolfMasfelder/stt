# ADR-07: Authentifizierung und Autorisierung via OAuth2/OIDC

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** FA-15, QA-6, RB-10

## Kontext

Bisher ist die API unauthentifiziert. Für den Produktbetrieb müssen Zugriffe authentifiziert werden. Es gibt verschiedene Ansätze: API-Keys, HTTP Basic Auth, OAuth2/OIDC, mTLS.

## Entscheidung

OAuth2 mit OpenID Connect (OIDC) als Authentifizierungs- und Autorisierungsstandard.

### Varianten zur Evaluierung

| Option | Beschreibung | Bewertung |
|--------|-------------|-----------|
| **A: Externer OIDC-Provider (Keycloak)** | Self-hosted Keycloak als Identity Provider im Docker-Stack | Vollständig, aber ressourcenintensiv |
| **B: Externer OIDC-Provider (EU-SaaS)** | z. B. Zitadel (Schweiz), Authentik (Self-Hosted) | Weniger Wartung, EU-konform |
| **C: Eigene Auth-Schicht** | Eigene JWT-Ausstellung in FastAPI | Weniger Abhängigkeiten, aber Eigenimplementierung von Security ist riskant |

### Empfehlung

**Option A oder B** — Keycloak oder Zitadel. Keine Eigenimplementierung von Authentifizierung (Security-Antipattern).

### Details

- **Client-Flow:** Authorization Code Flow mit PKCE (für Mobile App)
- **Token-Format:** JWT (JSON Web Tokens)
- **Token-Lebensdauer:** Access-Token 15 min, Refresh-Token 7 Tage
- **Validierung:** Server validiert JWT-Signatur gegen OIDC-Discovery-Endpoint
- **Rollen:** `user` (Standard), `admin` (Benutzerverwaltung, Storage-Config)

## Begründung

- OAuth2/OIDC ist der Industriestandard für APIs und Mobile Apps
- PKCE schützt gegen Authorization Code Interception (Mobile-spezifisch)
- JWT ermöglicht zustandslose Token-Validierung auf dem Server
- Externe Identity Provider sind battle-tested und auditierbar
- Keycloak und Zitadel sind Open Source und DSGVO-kompatibel

## Konsequenzen

- Identity Provider muss deployt und betrieben werden
- FastAPI-Middleware für JWT-Validierung erforderlich
- Mobile App muss OAuth2-Flow mit PKCE implementieren
- CLI-Client braucht Device Authorization Grant oder Client Credentials Flow
- Benutzerverwaltung über den Identity Provider (nicht in der STT-App)

## Offene Fragen

- [ ] Welcher Identity Provider? (Keycloak vs. Zitadel vs. Authentik)
- [ ] Self-hosted oder managed?
- [ ] Wie wird der CLI-Client authentifiziert? (Device Flow vs. Service Account)
