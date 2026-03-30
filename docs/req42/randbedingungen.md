# Randbedingungen

## Technisch

| ID | Randbedingung | Begründung |
|----|---------------|------------|
| RB-1 | Python 3.13 | Server-Backend, aktuelle Python-Version |
| RB-2 | Django 5.x + Django REST Framework | Web-Framework mit eingebautem ORM, Auth, Admin, Migrations — ersetzt FastAPI (ADR-15) |
| RB-3 | Docker / Docker Compose | Container-basiertes Deployment auf Remote-Server |
| RB-4 | faster-whisper | Effiziente lokale Whisper-Implementierung (CTranslate2) |
| RB-5 | pyannote.audio 4.x | State-of-the-art Speaker Diarization, läuft lokal |
| RB-6 | LM Studio | Lokales LLM-Hosting, OpenAI-kompatible API |
| RB-7 | HuggingFace-Token | Erforderlich für pyannote-Modell-Download (einmalig) |
| RB-8 | Kein GPU lokal | CPU-Verarbeitung auf lokalem Rechner, GPU optional auf Server |
| RB-9 | TLS 1.3 | Verschlüsselte Kommunikation zwischen allen Komponenten (Zero-Trust) |
| RB-10 | OAuth2 / OIDC | Standardisierte Authentifizierung und Autorisierung |
| RB-11 | EU-Hosting | Alle Dienste und Daten ausschließlich bei europäischen Anbietern |
| RB-12 | PostgreSQL | Datenbank für alle Szenarien (Jobs, Config, Audit-Log, User); eliminiert SQLite→PostgreSQL-Migration |
| RB-13 | Linux (openSUSE) | Entwicklungs- und Server-Zielplattform |
| RB-14 | Cross-Platform Mobile App (Android + iOS) | Eine Codebase für beide Plattformen; Framework-Entscheidung vor Phase 2c erforderlich (ADR-10) |
| RB-15 | Sichere Credential-Speicherung auf dem Gerät | Android Keystore / iOS Keychain für OAuth2-Tokens und Konfigurationsdaten |
| RB-16 | iOS-Tests initial nur über Simulator/CI | Derzeit keine iOS-Testgeräte verfügbar; Android-Geräte als primäre Testplattform |

## Organisatorisch

| ID | Randbedingung | Begründung |
|----|---------------|------------|
| RB-20 | Einzelentwickler-Projekt | Keine Team-Koordination nötig |
| RB-21 | Keine nicht-europäischen Cloud-Dienste | Datenschutz / DSGVO — keine Datenverarbeitung außerhalb der EU |
| RB-22 | DSGVO-Konformität | Verpflichtend bei Verarbeitung personenbezogener Daten (Audio-Aufnahmen mit Stimmen) |
| RB-23 | Zero-Trust als Sicherheitsparadigma | Kein implizites Vertrauen in Netzwerkgrenzen oder Clients |

## Regulatorisch

| ID | Randbedingung | Begründung |
|----|---------------|------------|
| RB-30 | DSGVO (Verordnung (EU) 2016/679) | Personenbezogene Daten (Stimmen, Sprecherzuordnung) erfordern vollständige DSGVO-Konformität |
| RB-31 | Aufbewahrungspflichten | Audio- und Textdaten dürfen nur so lange gespeichert werden wie nötig |
| RB-32 | Informationspflicht (Art. 13/14) | Nutzer müssen über Datenverarbeitung informiert werden |
| RB-33 | Auftragsverarbeitung (Art. 28) | Bei externem Hosting ist ein AV-Vertrag erforderlich |
