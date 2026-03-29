# ADR-15: Migration von FastAPI zu Django/DRF mit PostgreSQL

**Status:** Entschieden
**Datum:** 2026-03-28
**Bezug:** RB-2, RB-12, ADR-07, ADR-12, ADR-14

## Kontext

Die bestehende STT-API nutzt FastAPI (~230 Zeilen in `server.py`). Für die Produktexpansion (Phase 2) werden folgende Fähigkeiten benötigt:

- Authentifizierung und Autorisierung (OAuth2)
- Job-Queue für asynchrone Verarbeitung
- Datenbank-Migrationen
- Admin-Oberfläche für Mandanten-Verwaltung (SaaS)
- OpenAPI-Dokumentation

FastAPI bietet diese Funktionen nicht out-of-the-box und erfordert zahlreiche externe Libraries mit eigener Integrations- und Wartungslast.

## Entscheidung

Migration von FastAPI zu **Django 5.x + Django REST Framework (DRF)** mit **PostgreSQL** als Datenbank für alle Deployment-Szenarien.

### Bewertung

| Kriterium | FastAPI + Plugins | Django + DRF |
|-----------|-------------------|--------------|
| Auth | python-jose + eigener Code | django-oauth-toolkit (DOT) |
| Job-Queue | Celery + Redis + Broker | django-q2 (ORM-Broker, kein Redis nötig) |
| Migrationen | Alembic (manuell) | Django Migrations (integriert) |
| Admin-UI | Keines | Django-Admin (integriert) |
| OpenAPI | FastAPI (integriert) | drf-spectacular (automatisch aus ViewSets) |
| ORM | SQLAlchemy (separat) | Django ORM (integriert) |
| Security | Manuell (Middleware) | SecurityMiddleware, CSRF, `check --deploy` |
| Aufwand | Viele Einzelteile integrieren | Batteries included |

### Django-Module

| Modul | Zweck |
|-------|-------|
| `django` | Web-Framework, ORM, Migrations, Admin |
| `djangorestframework` | REST-API ViewSets, Serializers, Permissions |
| `python-dotenv` | Umgebungsvariablen-Konfiguration (.env) — einheitlich mit config.py |
| `django-oauth-toolkit` | OAuth2-Provider (InHouse/Dedicated), Resource Server (SaaS) |
| `drf-spectacular` | OpenAPI 3.0 Schema-Generierung |
| `django-q2` | Task-Queue mit ORM-Broker (kein Redis nötig) |
| `psycopg[binary]` | PostgreSQL-Adapter |
| `gunicorn` | WSGI-Server für Produktion |
| `django-cors-headers` | CORS-Konfiguration |

### Datenbank

PostgreSQL für alle Szenarien:

| Szenario | PostgreSQL-Setup |
|----------|-----------------|
| InHouse | Docker-Container (`postgres:16-alpine`) |
| Dedicated | Managed PostgreSQL oder Container |
| SaaS | Managed PostgreSQL, Schema-Isolation pro Mandant |

### Migrationsaufwand

- Geschäftslogik (`transcribe.py`, `diarize.py`, `summarize.py`, `whisper_common.py`, `prompts.py`) ist vollständig framework-unabhängig → **keine Änderung**
- Nur `server.py` (~230 Zeilen) muss auf DRF ViewSets umgeschrieben werden
- Geschätzter Aufwand: ~5 Arbeitstage

## Begründung

- **Ein Solo-Entwickler** profitiert maximal von Djangos Batteries-Included-Ansatz
- Alle benötigten Fähigkeiten (Auth, Queue, Migrations, Admin) sind als getestete Django-Pakete verfügbar
- PostgreSQL eliminiert das SQLite→PostgreSQL-Migrationsproblem bei Szenario-Wechsel
- Die Geschäftslogik ist bereits entkoppelt — der Migrationsaufwand beschränkt sich auf die HTTP-Schicht
- Async-Performance von FastAPI ist für ML-Workloads irrelevant (GPU/CPU-bound, nicht I/O-bound)

## Konsequenzen

- `requirements.txt` aktualisiert (FastAPI/Uvicorn entfernt, Django-Stack hinzugefügt)
- `server.py` wird auf DRF ViewSets umgeschrieben (Phase 2a)
- PostgreSQL als zusätzlicher Container im Docker-Stack
- Django-Admin als Verwaltungsoberfläche für InHouse/Dedicated
- Alle betroffenen ADRs aktualisiert (ADR-07, ADR-12, ADR-14)
- Randbedingung RB-2 aktualisiert auf Django 5.x + DRF

## Offene Fragen

- [ ] Django-Projektstruktur: Monolithisch oder als Django-App innerhalb des Projekts?
- [ ] Gunicorn-Worker-Anzahl und -Typ (sync vs. gthread) für ML-Workloads?
