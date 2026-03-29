# ADR-14: API-Sicherheit und Härtung

**Status:** Aktualisiert
**Datum:** 2026-03-28 (aktualisiert nach ADR-15)
**Bezug:** QA-11, QA-6, ADR-15

## Kontext

Die API muss für den Produktbetrieb (öffentlich erreichbar) gegen die OWASP Top 10 und weitere Angriffsvektoren gehärtet werden. Durch die Migration auf Django/DRF (ADR-15) stehen integrierte Security-Mechanismen zur Verfügung.

## Entscheidung

### Security-Maßnahmen

| Maßnahme | Umsetzung |
|----------|-----------|
| **Input-Validierung** | DRF Serializers (Typ-Validierung, Feldlängen), zusätzlich: Dateigrößen-Limits, MIME-Type-Validierung |
| **Rate Limiting** | DRF Throttling (`AnonRateThrottle`, `UserRateThrottle`): z. B. 10 Requests/Minute für Upload-Endpoints |
| **Security Headers** | `django.middleware.security.SecurityMiddleware` (HSTS, X-Content-Type-Options, X-Frame-Options) |
| **CORS** | `django-cors-headers` — Whitelist konfigurierbar, kein `*` in Produktion |
| **CSRF** | Django CSRF-Middleware (für Browser-Clients), DRF `SessionAuthentication` |
| **Request Size Limit** | `DATA_UPLOAD_MAX_MEMORY_SIZE` + Reverse-Proxy-Limit (Default: 500 MB für Audio) |
| **Authentication** | Bearer Token via `django-oauth-toolkit` (siehe ADR-07) |
| **Logging** | Security-relevante Events loggen (Failed Auth, Rate Limit Hits) |
| **Dependency Scanning** | Regelmäßige Prüfung auf bekannte Schwachstellen in Dependencies |
| **Deployment Check** | `python manage.py check --deploy` vor jedem Release |

### Reverse-Proxy-Konfiguration

```
Internet → Caddy/Traefik (TLS, Headers) → Gunicorn + Django (:8090)
```

**Empfehlung:** Caddy als Reverse-Proxy:
- Automatisches TLS via Let's Encrypt
- Einfache Konfiguration
- Minimaler Ressourcenverbrauch
- In Go geschrieben (keine Runtime-Abhängigkeiten)

### OWASP Top 10 Abdeckung

| OWASP | Risiko | Maßnahme |
|-------|--------|----------|
| A01 | Broken Access Control | DRF Permissions (`IsAuthenticated`, `DjangoModelPermissions`), DOT Scopes |
| A02 | Cryptographic Failures | TLS 1.3, AES-256-GCM at Rest |
| A03 | Injection | Django ORM (parametrisierte Queries), DRF Serializer-Validierung |
| A04 | Insecure Design | Zero-Trust-Architektur, Threat Modeling |
| A05 | Security Misconfiguration | `manage.py check --deploy`, keine Default-Credentials |
| A06 | Vulnerable Components | Dependency Scanning (pip-audit, safety) |
| A07 | Auth Failures | django-oauth-toolkit, kein Eigen-Auth (siehe ADR-07) |
| A08 | Data Integrity Failures | Django CSRF-Middleware, signierte Tokens (DOT) |
| A09 | Logging Failures | Audit-Logging aller Security-Events |
| A10 | SSRF | Kein User-gesteuerter URL-Fetch, Storage-URLs validieren |

## Begründung

- Django bietet Security-Middleware out-of-the-box (CSRF, XSS, Clickjacking)
- DRF Throttling ist integriert und konfigurierbar pro View/User
- `manage.py check --deploy` prüft automatisch auf Security-Fehlkonfigurationen
- Django ORM verhindert SQL-Injection systemisch (keine Raw-Queries nötig)
- Reverse-Proxy entlastet die Anwendung von TLS-Terminierung

## Konsequenzen

- Caddy/Traefik als zusätzlicher Container im Docker-Stack
- Django SecurityMiddleware aktivieren und konfigurieren
- DRF Throttling-Klassen pro ViewSet konfigurieren
- `manage.py check --deploy` in CI/CD-Pipeline integrieren
- Regelmäßiges Dependency-Scanning in der Build-Pipeline

## Offene Fragen

- [ ] Caddy oder Traefik als Reverse-Proxy?
- [ ] Wie wird Rate Limiting konfiguriert (pro User, pro IP)?
- [ ] Soll ein WAF (Web Application Firewall) eingesetzt werden?
