# ADR-14: API-Sicherheit und Härtung

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** QA-11, QA-6

## Kontext

Die bestehende FastAPI-API ist für den LAN-Betrieb konzipiert und hat keine Sicherheitshärtung. Für den Produktbetrieb (öffentlich erreichbar) muss die API gegen die OWASP Top 10 und weitere Angriffsvektoren gehärtet werden.

## Entscheidung

### Security-Maßnahmen

| Maßnahme | Umsetzung |
|----------|-----------|
| **Input-Validierung** | Pydantic-Modelle (bereits vorhanden), zusätzlich: Dateigrößen-Limits, MIME-Type-Validierung |
| **Rate Limiting** | Middleware oder Reverse-Proxy: z. B. 10 Requests/Minute für Upload-Endpoints |
| **Security Headers** | HSTS, X-Content-Type-Options, X-Frame-Options, Content-Security-Policy |
| **CORS** | Whitelist konfigurierbar, kein `*` in Produktion |
| **Request Size Limit** | Max. Upload-Größe konfigurierbar (Default: 500 MB für Audio) |
| **Authentication** | Bearer Token (JWT) via OAuth2 (siehe ADR-07) |
| **Logging** | Security-relevante Events loggen (Failed Auth, Rate Limit Hits) |
| **Dependency Scanning** | Regelmäßige Prüfung auf bekannte Schwachstellen in Dependencies |

### Reverse-Proxy-Konfiguration

```
Internet → Caddy/Traefik (TLS, Rate Limit, Headers) → FastAPI (:8090)
```

**Empfehlung:** Caddy als Reverse-Proxy:
- Automatisches TLS via Let's Encrypt
- Einfache Konfiguration
- Minimaler Ressourcenverbrauch
- In Go geschrieben (keine Runtime-Abhängigkeiten)

### OWASP Top 10 Abdeckung

| OWASP | Risiko | Maßnahme |
|-------|--------|----------|
| A01 | Broken Access Control | OAuth2/OIDC, Rollen-basierte Zugriffskontrolle |
| A02 | Cryptographic Failures | TLS 1.3, AES-256-GCM at Rest |
| A03 | Injection | Pydantic-Validierung, keine SQL-Direkt-Queries |
| A04 | Insecure Design | Zero-Trust-Architektur, Threat Modeling |
| A05 | Security Misconfiguration | Härtungs-Checkliste, keine Default-Credentials |
| A06 | Vulnerable Components | Dependency Scanning (pip-audit, safety) |
| A07 | Auth Failures | Externe OIDC-Provider, kein Eigen-Auth |
| A08 | Data Integrity Failures | Signierte JWT-Tokens, Integritätsprüfung |
| A09 | Logging Failures | Audit-Logging aller Security-Events |
| A10 | SSRF | Kein User-gesteuerter URL-Fetch, Storage-URLs validieren |

## Begründung

- Öffentlich erreichbare API = Angriffsfläche
- OWASP Top 10 ist der Mindeststandard für Web-API-Sicherheit
- Reverse-Proxy entlastet die Anwendung von TLS und Rate Limiting
- Caddy ist leichtgewichtig und hat automatisches Zertifikatsmanagement

## Konsequenzen

- Caddy/Traefik als zusätzlicher Container im Docker-Stack
- Security-Header-Middleware in FastAPI oder im Reverse-Proxy
- Rate-Limiting-Konfiguration
- Regelmäßiges Dependency-Scanning in der Build-Pipeline
- Härtungs-Checkliste für Deployment

## Offene Fragen

- [ ] Caddy oder Traefik als Reverse-Proxy?
- [ ] Wie wird Rate Limiting konfiguriert (pro User, pro IP)?
- [ ] Soll ein WAF (Web Application Firewall) eingesetzt werden?
