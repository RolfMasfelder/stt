# Umsetzungsplan — STT Produktausbau

## Ausgangsprompt

> Das bestehenden Client/Server-System soll zu einem Produkt ausgebaut werden. Als Frontend stelle ich mir eine App auf einem Handy vor, das mit seinem Mikrofon ein Gespräch aufnehmen und dann an den Server schicken kann. Einen PC-gestützen Client, bisher ohne Aufnahme-Funktion, gibt es ja schon.
> Die Server-Komponente kann lokal auf einer leistungsfähigen Hardware oder bei einem Internet-Provider laufen. Das Frontend muss so weit konfigurierbar sein, das die Kommunikation mit dem Server hergestellt werden kann. Also keine hart codierten Verbindungseinstellungen. Möglicherweise kommen später noch konfigurierbare Ablageorte für die Ergebnisse der Verarbeitung dazu. Dann soll der Server die Dateien nicht einfach zurückgeben, was trotzdem als default Ablageort weiter möglich sein soll, sondern kann die Dateien auch auf einen File-Storage ablegen. Die Konfigurationen für die Ablageorte sollen auch im Frontend erstellt werden können und dann an den Server übertragen werden. Dazu sind auch entsprechende Testfunktionen im Server notwendig um dem Frontend ein Feedback geben zu können, das die Konfiguration erfolgreich war.
> Allgemeine Anforderung an dieses Produkt ist: Zero-Trust! Aus Datenschutzgründen werden nur Europäische Dienstleister in Betracht gezogen. Das Ergebniss soll DSGVO-konform sein.
> Nur authentifizierte Anwender dürfen Zugreifen. Alle Daten sind verschlüsselt, sowohl gespeicherte als auch übertragene Daten.
> Das sind die Anforderungen die mir bisher einfallen, es können weiter hinzukommen.

### Klarstellung: Deployment-Szenarien (Iteration 2)

> Die server-Komponente kann auch 'InHouse' betrieben werden. Bei besonders datenschutzsensiblen Anwendern (Anwälte, Notare, Ärzte) kann der Bedarf bestehen, das die Daten niemals das Haus verlassen dürfen. Dies ist aber nur ein mögliches Scenario. Zweites Scenario: der Betrieb bei einem Hoster, ein Kunde eine Serverkomponente, also kein multitenant System. Dritte Variante, die große Lösung, als SaaS bei einem EU-Hoster, dann aber multitenant/multiuser. Die letzte Version wird eine Kubernetes-Konfiguration mit automatischer horizontaler Skalierung.

### Klarstellung: Sichtkontrolle und Korrektur (Iteration 2)

> Da die Umsetzung von Sprache zu Text fehlerbehaftet ist muss eine Möglichkeit zur Sichtkontrolle und Korrektur der Zwischenergebnisse bestehen. Also die Dateien, die derzeit als *_sprecher, *_struktur und *_zusammenfassung erzeugt werden müssen nach manueller Korrektur noch einmal 'weiterverarbeitet' werden können.

---

## 1. Übersicht der Anforderungen

### Direkt formulierte Anforderungen

| # | Anforderung | Dokumentiert in |
|---|-------------|-----------------|
| 1 | Mobile App mit Audio-Aufnahme | FA-10, FA-11 |
| 2 | Konfigurierbare Server-Verbindung (kein Hardcoding) | FA-12 |
| 3 | Konfigurierbare Ablageorte (Storage Backends) | FA-13, ADR-11 |
| 4 | Storage-Konfiguration vom Frontend an Server | FA-13, ADR-12 |
| 5 | Test-Funktionen für Storage-Konfiguration | FA-14, ADR-12 |
| 6 | Zero-Trust-Sicherheitsarchitektur | QA-6, ADR-06 |
| 7 | Nur europäische Dienstleister (DSGVO) | QA-9, ADR-09 |
| 8 | DSGVO-Konformität | QA-7, ADR-13 |
| 9 | Authentifizierung aller Zugriffe | FA-15, ADR-07 |
| 10 | Verschlüsselung (Transport + Speicherung) | QA-8, ADR-08 |
| 11 | InHouse-Betrieb (On-Premises) für datenschutzsensible Kunden | ADR-09 |
| 12 | Dedicated Hosting (Single-Tenant) bei EU-Hoster | ADR-09 |
| 13 | SaaS Multi-Tenant mit Kubernetes + Auto-Skalierung | ADR-09 |
| 14 | Sichtkontrolle und Korrektur von Zwischenergebnissen | FA-18 |

### Abgeleitete Anforderungen (Best Practices)

| # | Anforderung | Begründung | Dokumentiert in |
|---|-------------|------------|------------------|
| 15 | Audit-Logging | DSGVO Art. 30 (Verarbeitungsverzeichnis) | FA-16 |
| 16 | Recht auf Löschung | DSGVO Art. 17 | FA-17 |
| 17 | API-Härtung (OWASP Top 10) | Zero-Trust + öffentliche Erreichbarkeit | QA-11, ADR-14 |
| 18 | Rate Limiting | Schutz gegen Missbrauch (DoS) | ADR-14 |
| 19 | Security Headers | OWASP Best Practice | ADR-14 |
| 20 | Reverse-Proxy mit TLS | Zero-Trust, Verschlüsselung | ADR-08, ADR-14 |
| 21 | Datenminimierung + Auto-Delete | DSGVO Art. 5 | ADR-13 |
| 22 | Offline-Fähigkeit der App | Mobile UX Best Practice | QA-10 |

---

## 2. Architektur-Zielbild

### Gemeinsame Komponenten (alle Szenarien)

```
  Clients                                          Server-Komponenten
  ─────────                                        ──────────────────
┌─────────────────────┐                          ┌─────────────────────────┐
│  Mobile App         │                          │  STT-Server (Django)    │
│  (Flutter/KMP)      │       HTTPS/TLS 1.3     │  ├── JWT-Validierung    │
│  ├── Audio-Aufnahme │ ──────────────────────►  │  ├── Transcription      │
│  ├── OAuth2 (PKCE)  │                          │  ├── Diarization        │
│  └── Konfiguration  │                          │  ├── Summarization      │
└─────────────────────┘                          │  ├── Config-API         │
                                                 │  ├── Korrektur-API      │
┌─────────────────────┐                          │  └── Audit-Logging      │
│  CLI-Client         │       HTTPS/TLS 1.3     └──────────┬──────────────┘
│  (Python)           │ ──────────────────────►             │
│  ├── OAuth2         │                          ┌──────────┴──────────────┐
│  └── Konfiguration  │                          │  Abhängige Dienste      │
└─────────────────────┘                          │  ├── Identity Provider  │
                                                 │  ├── LLM-Backend        │
                                                 │  ├── Storage Backends   │
                                                 │  └── Datenbank          │
                                                 └─────────────────────────┘
```

### Szenario 1: InHouse (On-Premises)

```
  Kanzlei / Praxis / Behörde (LAN, kein Internet)
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                                                                          │
 │  ┌──────────┐   LAN/TLS     ┌───────────────────────────────────────┐   │
 │  │ Mobile   │ ────────────► │  Docker Compose (lokaler Server)      │   │
 │  │ App      │               │                                       │   │
 │  └──────────┘               │  ┌─────────────┐  ┌───────────────┐   │   │
 │                             │  │ Caddy       │  │ STT-Server    │   │   │
 │  ┌──────────┐   LAN/TLS    │  │ (Self-Sign) │─►│ (Django)      │   │   │
 │  │ CLI      │ ────────────► │  └─────────────┘  └───────┬───────┘   │   │
 │  │ Client   │               │                           │           │   │
 │  └──────────┘               │  ┌────────────────────────┴────────┐  │   │
 │                             │  │ Ollama/LM Studio  │  PostgreSQL │  │   │
 │                             │  │ faster-whisper    │  Lokal-FS   │  │   │
 │                             │  │ pyannote.audio    │  Keycloak   │  │   │
 │                             │  └─────────────────────────────────┘  │   │
 │                             └───────────────────────────────────────┘   │
 │                                                                          │
 │  ✓ Keine Daten verlassen das Gebäude                                    │
 │  ✓ Self-Signed-Zertifikate oder internes CA                             │
 │  ✓ Offline-fähig (kein Internet zur Laufzeit)                           │
 └──────────────────────────────────────────────────────────────────────────┘
```

### Szenario 2: Dedicated Hosting (Single-Tenant)

```
  Kunde (Internet)                        EU-Hoster (Hetzner/IONOS/OVH)
 ┌──────────────────┐                    ┌──────────────────────────────────────┐
 │                  │                    │  Dedizierter Server (1 Kunde)        │
 │  ┌──────────┐   │   HTTPS/TLS 1.3   │                                      │
 │  │ Mobile   │   │ ────────────────►  │  ┌─────────────┐  ┌──────────────┐  │
 │  │ App      │   │                    │  │ Caddy       │  │ STT-Server   │  │
 │  └──────────┘   │                    │  │ (Let's Enc) │─►│ (Django)     │  │
 │                  │                    │  └─────────────┘  └──────┬───────┘  │
 │  ┌──────────┐   │   HTTPS/TLS 1.3   │                          │          │
 │  │ CLI      │   │ ────────────────►  │  ┌───────────────────────┴───────┐  │
 │  │ Client   │   │                    │  │ vLLM/Ollama   │  PostgreSQL  │  │
 │  └──────────┘   │                    │  │ faster-whisper │  S3 (EU)     │  │
 │                  │                    │  │ pyannote.audio │  Keycloak    │  │
 └──────────────────┘                    │  └───────────────────────────────┘  │
                                         │                                      │
                                         │  ✓ Let's Encrypt Zertifikate        │
                                         │  ✓ Ein Kunde = ein Server            │
                                         │  ✓ AV-Vertrag mit Hoster             │
                                         └──────────────────────────────────────┘
```

### Szenario 3: SaaS (Multi-Tenant, Kubernetes)

```
  Kunden (Internet)                       EU-Hoster — Kubernetes-Cluster
 ┌──────────────────┐                    ┌────────────────────────────────────────────┐
 │  Kunde A         │                    │                                            │
 │  ├── App         │   HTTPS/TLS 1.3   │  ┌──────────────────────────────────────┐  │
 │  └── CLI         │ ────────────────►  │  │  Ingress Controller (TLS, Routing)   │  │
 │                  │                    │  └──────────────┬───────────────────────┘  │
 │  Kunde B         │                    │                 │                          │
 │  ├── App         │ ────────────────►  │                 ▼                          │
 │  └── CLI         │                    │  ┌──────────────────────────────────────┐  │
 │                  │                    │  │  STT-Server Pods (Auto-Scaling HPA)  │  │
 │  Kunde C         │                    │  │  ├── Pod 1 (Kunde A Request)         │  │
 │  └── App         │ ────────────────►  │  │  ├── Pod 2 (Kunde B Request)         │  │
 │  ...             │                    │  │  └── Pod n (auto-skaliert)            │  │
 └──────────────────┘                    │  └──────────────┬───────────────────────┘  │
                                         │                 │                          │
                                         │  ┌──────────────┴───────────────────────┐  │
                                         │  │  Shared Services                      │  │
                                         │  │  ├── Keycloak/Zitadel (Multi-Realm)  │  │
                                         │  │  ├── PostgreSQL (Tenant-Isolation)    │  │
                                         │  │  ├── S3 Storage (Bucket-per-Tenant)  │  │
                                         │  │  └── Prometheus + Grafana            │  │
                                         │  └──────────────────────────────────────┘  │
                                         │                                            │
                                         │  ┌──────────────────────────────────────┐  │
                                         │  │  GPU-Node-Pool                        │  │
                                         │  │  ├── vLLM Pods (LLM-Verarbeitung)    │  │
                                         │  │  ├── Whisper Pods (Transkription)     │  │
                                         │  │  └── pyannote Pods (Diarization)      │  │
                                         │  └──────────────────────────────────────┘  │
                                         │                                            │
                                         │  ✓ Horizontale Auto-Skalierung (HPA)      │
                                         │  ✓ Mandantentrennung auf allen Ebenen      │
                                         │  ✓ GPU-Workloads separat skalierbar        │
                                         └────────────────────────────────────────────┘
```

### Übersicht Deployment-Szenarien (siehe ADR-09)

| Eigenschaft | InHouse | Dedicated | SaaS |
|-------------|---------|-----------|------|
| **Zielgruppe** | Anwälte, Notare, Ärzte (§ 203 StGB) | Unternehmen | Breiter Markt |
| **Deployment** | Docker Compose, lokale HW | Docker Compose, EU-Hoster | Kubernetes, EU-Hoster |
| **Skalierung** | Vertikal | Vertikal | Horizontal (HPA) |
| **Multi-Tenant** | Nein | Nein | Ja |
| **Internet** | Nein | Ja | Ja |
| **TLS** | Self-Signed / internes CA | Let's Encrypt | Ingress + Let's Encrypt |
| **LLM** | Ollama / LM Studio | vLLM / Ollama | vLLM (GPU-Pool) |
| **Datenbank** | PostgreSQL | PostgreSQL | PostgreSQL |
| **Storage** | Lokales Dateisystem | S3 (EU) / Lokal | S3 (Bucket-per-Tenant) |

---

## 3. Technologievorschläge

| Komponente | Empfehlung | Alternativen | ADR |
|------------|-----------|-------------|-----|
| **Web-Framework** | Django 5.x + Django REST Framework | FastAPI (bisherig) | ADR-15 |
| **Datenbank** | PostgreSQL (alle Szenarien) | — | ADR-15, RB-12 |
| **Task-Queue** | django-q2 (DB als Broker) | Celery + Redis | ADR-15 |
| **Mobile App** | Flutter oder Kotlin Multiplatform | React Native, PWA | ADR-10 |
| **Identity Provider** | django-oauth-toolkit (eingebaut) + optional externer IdP | Keycloak, Zitadel | ADR-07 |
| **Reverse-Proxy** | Caddy | Traefik, nginx | ADR-14 |
| **TLS-Zertifikate** | Let's Encrypt (via Caddy) | Manuell | ADR-08 |
| **Object Storage** | IONOS S3 oder OVH Object Storage | MinIO (Self-Hosted) | ADR-09, ADR-11 |
| **Verschlüsselung at Rest** | LUKS + AES-256-GCM (App-Level) | Nur LUKS | ADR-08 |
| **Hosting** | Hetzner Cloud (DE) | IONOS, Netcup, OVH | ADR-09 |
| **Container-Orchestrierung** | Docker Compose (Szenarien 1+2), Kubernetes (Szenario 3) | — | ADR-09 |
| **LLM (Produktion)** | vLLM oder Ollama | LM Studio (nur InHouse/Dev) | — |
| **API-Dokumentation** | drf-spectacular (OpenAPI 3.0) | — | ADR-15 |

---

## 4. Umsetzungsphasen

### Phase 2a: Sicherheits-Fundament (Priorität: Hoch)

**Ziel:** Migration auf Django/PostgreSQL und API absichern, bevor neue Features hinzukommen.

| Schritt | Beschreibung | Abhängigkeiten | ADR | Status |
|---------|-------------|----------------|-----|--------|
| 2a.0 | Django-Projekt aufsetzen, Business-Logic übernehmen, PostgreSQL-Container | — | ADR-15 | ✅ Fertig |
| 2a.1 | Django-Modelle (Job, StorageConfig, AuditLog) + Migrationen | 2a.0 | ADR-15 | ✅ Fertig |
| 2a.2 | ~~API-Endpoints mit DRF portieren~~ → in 2a.0 erledigt | — | — | ✅ Fertig |
| 2a.3 | Task-Queue mit django-q2 für asynchrone Verarbeitung | 2a.1 | ADR-15 | ✅ Fertig |
| 2a.4 | Reverse-Proxy (Caddy) vor Django schalten | 2a.0 | ADR-14 | ✅ Fertig |
| 2a.5 | TLS-Terminierung einrichten | 2a.4 | ADR-08 | ✅ Fertig |
| 2a.6 | OAuth2-Provider mit django-oauth-toolkit einrichten | 2a.0 | ADR-07 | ✅ Fertig |
| 2a.7 | JWT-Validierung über DRF-Permissions | 2a.6 | ADR-07 | ✅ Fertig |
| 2a.8 | Security-Header und Rate Limiting (DRF Throttling) | 2a.4 | ADR-14 | ✅ Fertig |
| 2a.9 | Audit-Logging implementieren | 2a.7 | FA-16 | ✅ Fertig |
| 2a.10 | CLI-Client auf OAuth2 umstellen | 2a.6 | ADR-07 | ✅ Fertig |

**Erledigt in 2a.0:** Django-Projektstruktur (`settings.py`, `urls.py`, `wsgi.py`), DRF-API-App (`stt.api`) mit 4 Endpoints (Health, Transcribe, Diarize, Process), Serializer für OpenAPI-Doku, PostgreSQL in `docker-compose.yml`, Gunicorn als WSGI-Server, `pyproject.toml` auf Django-Stack aktualisiert, alle 107 Tests portiert und bestanden. FastAPI/uvicorn entfernt.

**Erledigt in 2a.3:** django-q2 als Task-Queue mit PostgreSQL als Broker konfiguriert (`Q_CLUSTER` in `settings.py`). Drei async Task-Funktionen (`run_transcribe`, `run_diarize`, `run_process`) in `stt/api/tasks.py`. Neue Endpoints: `POST /v1/jobs` (erstellt Job + dispatcht Task, HTTP 202) und `GET /v1/jobs/{id}` (Status + Ergebnisse). AuditLog-Integration bei Job-Erstellung/-Abschluss/-Fehler. Worker-Service `stt-worker` in `docker-compose.yml` (`manage.py qcluster`). 19 neue Tests (143 gesamt). Docker-First-Workflow etabliert.

**Erledigt in 2a.4 + 2a.5:** Caddy 2 als Reverse-Proxy mit automatischem TLS in `docker-compose.yml` (Service `caddy`, Profil `production`). `Caddyfile` mit Security-Headers (HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy), Request-Size-Limit (500 MB), Health-Check auf `/health`. Django `SecurityMiddleware` aktiviert, `SECURE_PROXY_SSL_HEADER` für X-Forwarded-Proto, `USE_X_FORWARDED_HOST`. Produktions-Härtung (non-DEBUG): SSL-Redirect, Secure Cookies, HSTS 2 Jahre. Gunicorn nur intern erreichbar (expose statt ports). Caddy-Volumes für Zertifikatspersistenz. `SITE_ADDRESS` konfigurierbar (Default: self-signed, Domain = Let's Encrypt). 9 neue Tests (152 gesamt).

**Erledigt in 2a.6:** `django-oauth-toolkit` (DOT) als OAuth2-Provider integriert. `oauth2_provider` in INSTALLED_APPS, DOT-Migrationen angewendet (12 Tabellen). OAuth2-Konfiguration: Access-Token 15 Min, Refresh-Token 7 Tage, PKCE erzwungen, Token-Rotation. DRF Default-Auth auf `OAuth2Authentication` + `IsAuthenticated` gesetzt. Health-Endpoint bleibt öffentlich (`AllowAny`). OAuth2-URLs unter `/o/` (Token, Authorize, Revoke). Shared Test-Fixtures in `conftest.py` (`test_user`, `oauth2_token`, `auth_client`). 15 neue Tests (167 gesamt).

**Erledigt in 2a.7:** Scope-basierte Berechtigungen mit `TokenHasReadWriteScope` — GET-Requests benötigen `read`-Scope, POST-Requests `write`-Scope. `READ_SCOPE`/`WRITE_SCOPE` in DOT-Konfiguration. OpenAPI-Schema mit OAuth2-Flows (clientCredentials + authorizationCode) via drf-spectacular. 4 neue Tests (171 gesamt).

**Erledigt in 2a.8:** DRF Throttling mit drei Stufen: `AnonRateThrottle` (20/min), `UserRateThrottle` (60/min), custom `UploadRateThrottle` (10/min) für Upload-Endpoints. Throttle-Klasse in `stt/api/throttles.py`, angewendet auf TranscribeView, DiarizeView, ProcessView, JobCreateView. Security-Headers via SecurityMiddleware (Django) + Caddy Caddyfile. 4 neue Tests (175 gesamt).

**Erledigt in 2a.9:** Audit-Logging mit `log_audit()`-Helper (`stt/api/audit.py`) — extrahiert automatisch Actor (Username) und Client-IP (X-Forwarded-For / REMOTE_ADDR) aus Request. `AuditMiddleware` (`stt/api/middleware.py`) loggt Security-Events: AUTH_FAILED (401) und RATE_LIMITED (429). Alle bestehenden `AuditLog.objects.create()`-Aufrufe in `views.py` und `tasks.py` auf `log_audit()` migriert. Migration für neue AuditAction-Choices. 13 neue Tests (188 gesamt).

**Erledigt in 2a.10:** CLI-Client (`STTClient`) auf OAuth2 Client Credentials Flow umgestellt. Neues `OAuth2ClientConfig`-Dataclass in `config.py` mit Env-Variablen `OAUTH2_CLIENT_ID`, `OAUTH2_CLIENT_SECRET`, `OAUTH2_TOKEN_URL`, `OAUTH2_SCOPES`. Token-Akquise via `/o/token/`, automatisches Caching mit Refresh 30s vor Ablauf. `AuthenticationError` bei 401-Responses. Bearer-Token in allen API-Requests. `__main__.py` übergibt OAuth2-Config an Client wenn `token_url` gesetzt. `.env.example` mit OAuth2-Dokumentation. 10 neue Tests (198 gesamt).

**✅ Phase 2a abgeschlossen** — Alle Sicherheitsgrundlagen implementiert: Django/DRF, Caddy TLS, OAuth2-Provider + Client, Scoped Permissions, Rate Limiting, Audit-Logging.

### Phase 2b: Konfigurations-Infrastruktur

**Ziel:** Konfigurierbare Verbindungen und Storage Backends.

| Schritt | Beschreibung | Abhängigkeiten | ADR | Status |
|---------|-------------|----------------|-----|--------|
| 2b.1 | Storage-Backend-Abstraktion implementieren | — | ADR-11 | ✅ Done |
| 2b.2 | Config-API (DRF ViewSets + Test-Endpoints) | 2b.1, 2a.1 | ADR-12 | ✅ Done |
| 2b.3 | S3-Backend implementieren | 2b.1 | ADR-11 | ✅ Done |
| 2b.4 | Verschlüsselung at Rest einbauen | 2b.1 | ADR-08 | ✅ Done |
| 2b.5 | CLI konfigurierbare Server-URL (Verbesserung) | — | FA-12 | ✅ Done |
| 2b.6 | OpenAPI-Spezifikation via drf-spectacular generieren | 2b.2 | ADR-15 | ✅ Done |

### Phase 2c: Mobile App

**Ziel:** Erste mobile App mit Audio-Aufnahme und Server-Kommunikation.

| Schritt | Beschreibung | Abhängigkeiten | ADR |
|---------|-------------|----------------|-----|
| 2c.1 | App-Projekt aufsetzen (Flutter/KMP) | — | ADR-10 |
| 2c.2 | Audio-Aufnahme implementieren | 2c.1 | FA-10 |
| 2c.3 | Server-Verbindung konfigurierbar | 2c.1 | FA-12 |
| 2c.4 | OAuth2 PKCE-Flow | 2a.3, 2c.1 | ADR-07 |
| 2c.5 | Audio-Upload und Ergebnis-Anzeige | 2c.2, 2c.3, 2c.4 | FA-11 |
| 2c.6 | Storage-Konfiguration im Frontend | 2b.2, 2c.1 | FA-13, FA-14 |
| 2c.7 | Offline-Fähigkeit (Aufnahme ohne Server) | 2c.2 | QA-10 |

### Phase 2d: Korrektur-Workflow und API-Einzelschritte

**Ziel:** Sichtkontrolle und Korrektur von Zwischenergebnissen ermöglichen.

| Schritt | Beschreibung | Abhängigkeiten | Bezug |
|---------|-------------|----------------|-------|
| 2d.1 | REST-API für Einzelschritte (Struktur, Zusammenfassung separat aufrufbar) | — | FA-18 |
| 2d.2 | Versionierung von Zwischenergebnissen (Original + korrigiert) | 2d.1 | FA-18 |
| 2d.3 | Korrektur-Workflow im Frontend (Anzeige → Editieren → Weiterverarbeiten) | 2c.5, 2d.1 | FA-18 |

### Phase 2e: DSGVO-Konformität und Betrieb

**Ziel:** Regulatorische Anforderungen erfüllen, Produktionsbetrieb.

| Schritt | Beschreibung | Abhängigkeiten | ADR |
|---------|-------------|----------------|-----|
| 2e.1 | Lösch-API implementieren (Art. 17) | 2b.1 | FA-17 |
| 2e.2 | Auto-Delete-Mechanismus (Aufbewahrungsfrist) | 2e.1 | ADR-13 |
| 2e.3 | Datenexport-API (Art. 20) | 2b.1 | ADR-13 |
| 2e.4 | AV-Vertrag-Template erstellen | — | ADR-13 |
| 2e.5 | Datenschutzhinweise für App | — | ADR-13 |
| 2e.6 | Hosting einrichten (EU-Provider, Szenario 2) | — | ADR-09 |
| 2e.7 | Härtungs-Checkliste für Deployment | 2a.* | ADR-14 |

### Phase 2f: SaaS und Kubernetes

**Ziel:** Multi-Tenant SaaS-Betrieb mit horizontaler Skalierung.

| Schritt | Beschreibung | Abhängigkeiten | ADR |
|---------|-------------|----------------|-----|
| 2f.1 | Multi-Tenancy-Architektur (Daten-Isolation, Tenant-Kontext) | 2a.*, 2b.* | ADR-09 |
| 2f.2 | PostgreSQL mit Tenant-Isolation (Schema-per-Tenant oder RLS) | 2f.1 | ADR-09, ADR-12 |
| 2f.3 | Kubernetes-Deployment (Helm Charts) | 2f.1 | ADR-09 |
| 2f.4 | Horizontal Pod Autoscaler (HPA) | 2f.3 | ADR-09 |
| 2f.5 | GPU-Workload-Scheduling (Whisper, pyannote) | 2f.3 | ADR-09 |
| 2f.6 | Monitoring (Prometheus + Grafana) | 2f.3 | — |
| 2f.7 | Django-Admin anpassen für Multi-Tenant-Verwaltung | 2f.1 | ADR-09 |

---

## 5. Offene Entscheidungen (für Iterationen)

Die folgenden Punkte müssen vor oder während der Umsetzung geklärt werden:

### Technologie-Entscheidungen

- [ ] **Mobile Framework:** Flutter vs. Kotlin Multiplatform vs. andere?
- [ ] **Zielplattform:** Nur Android oder auch iOS?
- [x] ~~**Identity Provider:**~~ → django-oauth-toolkit als eingebauter OAuth2-Provider; externer IdP (Keycloak/Zitadel) optional für SaaS
- [x] ~~**Reverse-Proxy:**~~ → Caddy (automatisches TLS, einfache Konfiguration)
- [ ] **Hosting-Anbieter:** Hetzner vs. IONOS vs. Netcup vs. OVH?
- [ ] **Storage-Anbieter:** IONOS S3 vs. OVH vs. Self-Hosted MinIO?
- [x] ~~**Datenbank:**~~ → PostgreSQL für alle Szenarien (ADR-15)
- [x] ~~**Web-Framework:**~~ → Django 5.x + DRF (ADR-15)

### Architektur-Entscheidungen

- [ ] **GPU-Hosting:** Braucht der Provider GPU-Instanzen (für Whisper + pyannote)?
- [x] ~~**Multi-Tenancy:**~~ → Geklärt, siehe oben
- [ ] **App-Store-Vertrieb:** Soll die App über Google Play / Apple App Store vertrieben werden?
- [ ] **Monitoring:** Welche Monitoring-Lösung (Prometheus, Grafana)?

### DSGVO-Entscheidungen

- [ ] **Datenschutz-Folgenabschätzung (DSFA):** Ist eine DSFA erforderlich (Art. 35)?
- [ ] **Verantwortliche Stelle:** Wer ist Verantwortlicher — der Betreiber der Instanz?
- [ ] **Audio als biometrische Daten:** Fällt Sprechererkennung unter Art. 9 (besondere Kategorien)?
- [ ] **Einwilligung der Gesprächsteilnehmer:** Wie wird sichergestellt, dass alle Teilnehmer einer Aufnahme informiert/eingewilligt haben?

### Betrieb-Entscheidungen

- [ ] **Backup-Strategie:** Wie werden Daten und Konfigurationen gesichert?
- [ ] **Update-Strategie:** Rolling Updates, Blue-Green Deployment?
- [x] **Skalierung:** ~~Reicht eine einzelne Instanz oder Horizontal Scaling?~~ → Szenario-abhängig: InHouse/Dedicated = vertikal, SaaS = horizontal mit K8s HPA
- [ ] **InHouse Air-Gap-Updates:** Wie werden Offline-Installationen aktualisiert?
- [ ] **LM Studio Ersatz für Produktion:** vLLM, Ollama, oder llama.cpp Server für headless Betrieb?

---

## 6. Nächste Schritte

1. **Phase 2c starten** — Nächster Schritt: 2c.1 (App-Projekt aufsetzen)
2. **Iteration über Anforderungen** — Offene Entscheidungen (Abschnitt 5) klären
3. **Deployment-Szenario für Erstentwicklung festlegen** — Empfehlung: zuerst InHouse/Dedicated entwickeln, SaaS/K8s als spätere Phase
4. **ADRs finalisieren** — Phase-2a-ADRs (06, 07, 08, 14, 15) auf "Akzeptiert" setzen

---

## 7. Risiken

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| GPU-Hosting in EU teuer | Hoch | Hohe Betriebskosten | Hetzner GPU-Server, oder CPU-only mit längerer Verarbeitungszeit |
| LM Studio nicht server-tauglich | Mittel | Architekturänderung nötig | Alternative: vLLM, Ollama, llama.cpp Server |
| DSGVO-Risiko biometrische Daten | Mittel | DSFA erforderlich, ggf. Einschränkungen | Juristische Bewertung einholen |
| Einzelentwickler-Engpass | Hoch | Langsame Umsetzung | Phasenweise Umsetzung, MVP-Fokus |
| App-Store-Freigabe | Mittel | Verzögerung bei Vertrieb | PWA als Fallback |
