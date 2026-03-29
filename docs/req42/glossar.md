# Glossar

## Bestehende Begriffe

| Begriff | Definition |
|---------|------------|
| STT | Speech-to-Text — Umwandlung von gesprochener Sprache in Text |
| Transkription | Verschriftlichung einer Audio-Aufnahme |
| Diarization | Sprechererkennung — Zuordnung von Textabschnitten zu einzelnen Sprechern |
| faster-whisper | CTranslate2-basierte Implementierung von OpenAI Whisper, optimiert für CPU/GPU |
| faster-whisper-server | HTTP-Server mit OpenAI-kompatibler API für faster-whisper |
| pyannote.audio | Python-Framework für Audio-basierte Speaker Diarization |
| LM Studio | Desktop-Anwendung zum lokalen Betrieb von LLMs mit OpenAI-kompatibler API |
| LLM | Large Language Model — Großes Sprachmodell für Textverarbeitung |
| Pipeline | Verkettung mehrerer Verarbeitungsschritte (Transkription → Diarization → Strukturierung → Zusammenfassung) |
| HuggingFace | Plattform für ML-Modelle; hier nur für Modell-Download genutzt |
| CLI | Command Line Interface — Kommandozeilenschnittstelle |
| REST-API | HTTP-basierte Schnittstelle für programmatischen Zugriff |

## Neue Begriffe (Phase 2)

| Begriff | Definition |
|---------|------------|
| Zero-Trust | Sicherheitsparadigma: kein implizites Vertrauen — jeder Zugriff wird explizit authentifiziert und autorisiert, unabhängig von der Netzwerkposition |
| DSGVO | Datenschutz-Grundverordnung (Verordnung (EU) 2016/679) — europäisches Datenschutzrecht |
| GDPR | General Data Protection Regulation — englische Bezeichnung der DSGVO |
| OAuth2 | Autorisierungsframework (RFC 6749) für token-basierten Zugriff auf geschützte Ressourcen |
| OIDC | OpenID Connect — Authentifizierungsschicht auf Basis von OAuth2, liefert Identitätsinformationen |
| TLS | Transport Layer Security — kryptografisches Protokoll zur verschlüsselten Datenübertragung |
| mTLS | Mutual TLS — beidseitige Zertifikats-Authentifizierung zwischen Client und Server |
| Encryption at Rest | Verschlüsselung gespeicherter Daten (im Gegensatz zu Daten während der Übertragung) |
| Encryption in Transit | Verschlüsselung von Daten während der Netzwerkübertragung (via TLS) |
| Storage Backend | Austauschbarer Ablageort für Verarbeitungsergebnisse (z. B. lokales Dateisystem, S3, WebDAV) |
| S3-kompatibel | Speicher-API kompatibel mit dem Amazon S3-Protokoll (z. B. MinIO, Wasabi EU, IONOS S3) |
| WebDAV | Web-basiertes Protokoll für Dateizugriff (z. B. Nextcloud) |
| AV-Vertrag | Vertrag zur Auftragsverarbeitung nach DSGVO Art. 28 |
| Audit-Log | Manipulationssicheres Protokoll aller Zugriffe und Datenverarbeitungen |
| HSTS | HTTP Strict Transport Security — erzwingt HTTPS-Nutzung im Browser/Client |
| CORS | Cross-Origin Resource Sharing — Mechanismus für domänenübergreifende HTTP-Anfragen |
| Bearer Token | Zugangstoken, das als HTTP-Header (`Authorization: Bearer <token>`) übertragen wird |
| Rate Limiting | Begrenzung der Anzahl von API-Anfragen pro Zeiteinheit zum Schutz gegen Missbrauch |
| ADR | Architecture Decision Record — dokumentierte Architekturentscheidung |
| FA | Funktionale Anforderung (z. B. FA-10, FA-11) |
| QA | Qualitätsanforderung (z. B. QA-6, QA-7) |
| JWT | JSON Web Token (RFC 7519) — signiertes Token zur Übertragung von Identitäts- und Autorisierungsinformationen |
| PKCE | Proof Key for Code Exchange (RFC 7636) — Erweiterung des OAuth2-Authorization-Code-Flows für öffentliche Clients (z. B. Mobile Apps) |
| DSFA | Datenschutz-Folgenabschätzung (DSGVO Art. 35) — verpflichtende Risikoanalyse bei hohem Risiko für Betroffene |
| HPA | Horizontal Pod Autoscaler — Kubernetes-Mechanismus zur automatischen horizontalen Skalierung von Pods |
| K8s | Kurzform für Kubernetes — Container-Orchestrierungsplattform |
| SaaS | Software as a Service — Software als Dienstleistung über das Internet bereitgestellt |
| KMP | Kotlin Multiplatform — Framework zur plattformübergreifenden App-Entwicklung |
| PWA | Progressive Web App — Webanwendung mit nativen App-Funktionen |
| MVP | Minimum Viable Product — minimal funktionsfähiges Produkt |
| PoC | Proof of Concept — Machbarkeitsnachweis |
| OWASP | Open Web Application Security Project — Organisation für Webanwendungssicherheit (u. a. OWASP Top 10) |
| DoS | Denial of Service — Angriff zur Überlastung eines Dienstes |
| CRUD | Create, Read, Update, Delete — die vier grundlegenden Datenbankoperationen |
| RLS | Row-Level Security — zeilenbasierte Zugriffskontrolle in Datenbanken (z. B. PostgreSQL) |
| LUKS | Linux Unified Key Setup — Standard für Festplattenverschlüsselung unter Linux |
| AES-256-GCM | Advanced Encryption Standard mit 256-Bit-Schlüssel im Galois/Counter-Modus — authentifizierte Verschlüsselung |
| CA | Certificate Authority — Zertifizierungsstelle, die digitale Zertifikate ausstellt |
| GPU | Graphics Processing Unit — Grafikprozessor, hier für ML-Modell-Inferenz genutzt |
| CPU | Central Processing Unit — Hauptprozessor |
| vLLM | Hochperformanter LLM-Inferenz-Server mit PagedAttention für effizienten GPU-Speicher |
| Django | Python-Web-Framework mit integriertem ORM, Admin-Interface, Migrations und Auth-System |
| DRF | Django REST Framework — Toolkit für REST-APIs auf Basis von Django (ViewSets, Serializers, Permissions) |
| ORM | Object-Relational Mapping — Abstraktion zur Datenbank-Interaktion über Python-Klassen statt SQL |
| DOT | django-oauth-toolkit — OAuth2-Provider-Implementierung für Django |
| django-q2 | Task-Queue für Django mit ORM als Broker (kein separater Message-Broker wie Redis nötig) |
| drf-spectacular | OpenAPI-3.0-Schema-Generator für Django REST Framework |
| Gunicorn | WSGI-HTTP-Server für Python-Webanwendungen in Produktion |
| WSGI | Web Server Gateway Interface — Python-Standard-Schnittstelle zwischen Webserver und Anwendung |
| psycopg | PostgreSQL-Adapter für Python 3 (Version 3.x, asynchron-fähig) |
