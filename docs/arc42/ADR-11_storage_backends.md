# ADR-11: Konfigurierbare Storage Backends

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** FA-13, FA-14, Z-9

## Kontext

Bisher werden Ergebnisse direkt als HTTP-Response an den Client zurückgegeben. Künftig sollen Ergebnisse auch an konfigurierbaren Ablageorten gespeichert werden können (File-Storage). Der Default (direkte Rückgabe) bleibt erhalten.

## Entscheidung

Ein Storage-Backend-Abstraktionsschicht mit austauschbaren Implementierungen:

### Architektur

```
StorageBackend (Protocol / ABC)
├── DirectResponseBackend  (Default: Rückgabe an Client)
├── LocalFileBackend       (Lokales Dateisystem des Servers)
├── S3Backend              (S3-kompatibles Object Storage)
├── WebDAVBackend          (WebDAV, z. B. Nextcloud)
└── SFTPBackend            (SFTP-Server)
```

### Konfigurationsmodell

```python
@dataclass(frozen=True)
class StorageConfig:
    backend_type: str           # "direct", "local", "s3", "webdav", "sftp"
    endpoint: str | None        # URL/Host des Storage-Dienstes
    bucket_or_path: str | None  # Bucket-Name oder Verzeichnispfad
    credentials: str | None     # Referenz auf gespeicherte Credentials (nicht Klartext!)
    encrypt: bool = True        # Ergebnisse vor Speicherung verschlüsseln
```

### Priorität der Implementierung

1. **DirectResponseBackend** — Bestehendes Verhalten (Phase 1, bereits vorhanden)
2. **S3Backend** — S3-kompatibles Storage (EU-Anbieter: IONOS S3, OVH)
3. **LocalFileBackend** — Serverlokales Dateisystem
4. **WebDAVBackend** — Für Nextcloud-Integration
5. **SFTPBackend** — Niedrige Priorität

## Begründung

- Abstraktion über ein Interface/Protocol ermöglicht einfache Erweiterung
- S3-kompatibles Storage ist der De-facto-Standard für Object Storage
- EU-konforme S3-Anbieter verfügbar (IONOS, OVH)
- WebDAV relevant für Nextcloud-Nutzer (verbreitet in EU-Organisationen)
- Frozen Dataclass passt zum bestehenden Config-Muster (ADR-4)

## Konsequenzen

- Neue API-Endpoints: Storage-Konfiguration erstellen, testen, löschen
- Credentials müssen verschlüsselt gespeichert werden (Secrets Management)
- Storage-Test-Endpoint erforderlich (Schreib-/Lesezugriff prüfen)
- Asynchrone Speicherung möglich (Client wartet nicht auf Storage-Schreibvorgang)

## Offene Fragen

- [ ] Sollen mehrere Storage Backends gleichzeitig konfiguriert sein?
- [ ] Wie werden Storage-Credentials serverseitig gespeichert?
- [ ] Soll es eine Benachrichtigung geben, wenn die Storage-Speicherung fehlschlägt?
