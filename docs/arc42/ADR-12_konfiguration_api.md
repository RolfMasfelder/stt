# ADR-12: Konfigurations-API für Frontend-gesteuerte Einstellungen

**Status:** Aktualisiert
**Datum:** 2026-03-28 (aktualisiert nach ADR-15)
**Bezug:** FA-12, FA-13, FA-14, ADR-15

## Kontext

Konfigurationen (Server-Verbindung, Storage Backends) sollen im Frontend erstellt und an den Server übertragen werden. Durch die Entscheidung für Django/DRF (ADR-15) werden die Endpoints als DRF ViewSets mit Django ORM realisiert.

## Entscheidung

DRF ViewSets für Konfigurationsverwaltung mit PostgreSQL als Datenbank für alle Szenarien.

### API-Endpoints

```
# Storage-Konfiguration (DRF ViewSet + Custom Action)
POST   /api/v1/config/storage/          — Storage-Backend anlegen
GET    /api/v1/config/storage/          — Alle Storage-Backends auflisten
GET    /api/v1/config/storage/{id}/     — Ein Storage-Backend abrufen
PUT    /api/v1/config/storage/{id}/     — Storage-Backend aktualisieren
DELETE /api/v1/config/storage/{id}/     — Storage-Backend entfernen
POST   /api/v1/config/storage/{id}/test/ — Storage-Backend testen

# Test-Response-Format
{
    "status": "success" | "error",
    "checks": {
        "connection": true,
        "write": true,
        "read": true,
        "delete": true
    },
    "message": "Alle Prüfungen erfolgreich",
    "duration_ms": 342
}
```

### Autorisierung

- Alle Config-Endpoints erfordern `DjangoModelPermissions` (Rolle `admin`)
- Standard-Nutzer können nur ihre eigenen Verarbeitungsaufträge steuern
- Storage-Credentials werden per DRF Serializer mit `write_only=True` geschützt (kein Klartext-Rückgabe)

### Persistierung

PostgreSQL für alle Deployment-Szenarien (siehe ADR-15):

| Szenario | Datenbank |
|----------|-----------|
| InHouse | PostgreSQL (Docker-Container) |
| Dedicated | PostgreSQL (Managed oder Container) |
| SaaS | PostgreSQL (Managed, Schema-Isolation pro Mandant) |

## Begründung

- DRF ViewSets generieren CRUD-Endpoints automatisch mit konsistenter API
- Django ORM bietet Migrations, Validierung und Query-Abstraktion
- `write_only=True` in DRF Serializers verhindert Credential-Leaks elegant
- PostgreSQL für alle Szenarien eliminiert die SQLite→PostgreSQL-Migrationsproblematik
- `drf-spectacular` generiert OpenAPI-Dokumentation automatisch aus den ViewSets

## Konsequenzen

- DRF ViewSets und Serializers implementieren
- Django-Modelle für Storage-Konfiguration mit Migrations
- OpenAPI-Spezifikation wird automatisch via `drf-spectacular` generiert
- Frontend muss Config-Formulare bereitstellen
- Test-Endpoint muss tatsächlich gegen den Storage-Dienst prüfen (nicht nur Syntax)

## Offene Fragen

- [ ] Sollen Konfigurationen versioniert werden (Changelog)?
- [x] ~~Wie werden Konfigurationen zwischen Instanzen synchronisiert?~~ → PostgreSQL als Single Source of Truth
- [ ] Braucht der CLI-Client ebenfalls Zugriff auf die Config-API?
