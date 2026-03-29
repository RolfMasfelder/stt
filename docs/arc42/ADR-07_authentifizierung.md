# ADR-07: Authentifizierung und Autorisierung

**Status:** Aktualisiert
**Datum:** 2026-03-28 (aktualisiert nach ADR-15)
**Bezug:** FA-15, QA-6, RB-10, ADR-15

## Kontext

Bisher ist die API unauthentifiziert. Für den Produktbetrieb müssen Zugriffe authentifiziert werden. Durch die Entscheidung für Django (ADR-15) stehen mit `django-oauth-toolkit` (DOT) und dem Django-Permission-System integrierte Mechanismen zur Verfügung.

## Entscheidung

Gestuftes Authentifizierungsmodell je nach Szenario:

### Varianten

| Option | Beschreibung | Bewertung |
|--------|-------------|-----------|
| **A: django-oauth-toolkit (DOT)** | OAuth2-Provider direkt in Django integriert | Kein externer Dienst, ausreichend für InHouse/Dedicated |
| **B: Externer OIDC-Provider** | Keycloak / Zitadel für SaaS-Multi-Tenant | Notwendig bei mandantenübergreifender Identität |
| ~~C: Eigene Auth-Schicht~~ | ~~Eigene JWT-Ausstellung~~ | ~~Security-Antipattern — verworfen~~ |

### Empfehlung

- **InHouse / Dedicated:** Option A — django-oauth-toolkit als integrierter OAuth2-Provider
- **SaaS (Multi-Tenant):** Option B — externer OIDC-Provider (Keycloak / Zitadel), DOT als Resource Server

### Details

- **Client-Flow:** Authorization Code Flow mit PKCE (für Mobile App)
- **Token-Format:** OAuth2 Bearer Tokens (DOT) bzw. JWT bei externem IdP
- **Token-Lebensdauer:** Access-Token 15 min, Refresh-Token 7 Tage
- **Validierung InHouse/Dedicated:** DOT-interne Token-Validierung (DB-Lookup)
- **Validierung SaaS:** JWT-Signatur gegen OIDC-Discovery-Endpoint
- **Rollen:** Django Groups/Permissions — `user` (Standard), `admin` (Benutzerverwaltung, Storage-Config)
- **Berechtigungen:** DRF `IsAuthenticated`, `IsAdminUser`, Custom Permissions via `DjangoModelPermissions`

## Begründung

- DOT ist battle-tested (>5000 GitHub Stars) und direkt in Django integriert
- Kein externer Identity Provider für InHouse/Dedicated nötig → geringere Betriebskomplexität
- Django Groups/Permissions bieten feingranulare Zugriffskontrolle ohne Eigenimplementierung
- Bei SaaS-Skalierung bleibt der Wechsel auf externen IdP möglich (DOT als Resource Server)
- PKCE schützt gegen Authorization Code Interception (Mobile-spezifisch)

## Konsequenzen

- `django-oauth-toolkit` als Dependency (bereits in requirements.txt)
- Django-Admin für Benutzerverwaltung in InHouse/Dedicated
- Mobile App muss OAuth2-Flow mit PKCE implementieren
- CLI-Client nutzt Client Credentials Flow (DOT Application mit `grant_type=client_credentials`)
- Bei SaaS: externer IdP muss deployt und betrieben werden

## Offene Fragen

- [x] ~~Welcher Identity Provider?~~ → DOT für InHouse/Dedicated, externer IdP nur für SaaS
- [ ] Welcher externer IdP für SaaS? (Keycloak vs. Zitadel)
- [ ] Wie wird der CLI-Client authentifiziert? (Client Credentials via DOT)
