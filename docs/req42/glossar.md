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
