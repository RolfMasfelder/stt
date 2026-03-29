# ADR-12: Konfigurations-API für Frontend-gesteuerte Einstellungen

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** FA-12, FA-13, FA-14

## Kontext

Konfigurationen (Server-Verbindung, Storage Backends) sollen im Frontend erstellt und an den Server übertragen werden. Der Server benötigt entsprechende API-Endpoints zum Empfang, Speichern und Testen von Konfigurationen.

## Entscheidung

Neue REST-API-Endpoints für Konfigurationsverwaltung:

### API-Endpoints

```
# Storage-Konfiguration
POST   /v1/config/storage          — Storage-Backend anlegen
GET    /v1/config/storage           — Alle Storage-Backends auflisten
GET    /v1/config/storage/{id}      — Ein Storage-Backend abrufen
PUT    /v1/config/storage/{id}      — Storage-Backend aktualisieren
DELETE /v1/config/storage/{id}      — Storage-Backend entfernen
POST   /v1/config/storage/{id}/test — Storage-Backend testen

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

- Alle Config-Endpoints erfordern die Rolle `admin`
- Standard-Nutzer können nur ihre eigenen Verarbeitungsaufträge steuern
- Storage-Credentials werden nie im Klartext zurückgegeben (nur `*****`-Maskierung)

### Persistierung

Konfigurationen werden serverseitig in einer leichtgewichtigen Datenbank gespeichert:

| Option | Bewertung |
|--------|-----------|
| SQLite | Einfach, kein separater Dienst, gut für Einzelinstanzen |
| PostgreSQL | Für Multi-Instanz-Betrieb, EU-Hosting möglich |

**Empfehlung:** SQLite für v1, Migration auf PostgreSQL bei Bedarf.

## Begründung

- RESTful CRUD-Endpoints sind der Standard für Konfigurationsverwaltung
- Test-Endpoint gibt dem Frontend sofortiges Feedback
- Admin-Rolle verhindert unbefugte Konfigurationsänderungen
- Maskierung von Credentials verhindert Leak über die API

## Konsequenzen

- Neue Server-Endpoints implementieren
- Datenbank-Schema für Konfigurationsspeicherung
- OpenAPI-Spezifikation erweitern
- Frontend muss Config-Formulare bereitstellen
- Test-Endpoint muss tatsächlich gegen den Storage-Dienst prüfen (nicht nur Syntax)

## Offene Fragen

- [ ] Sollen Konfigurationen versioniert werden (Changelog)?
- [ ] Wie werden Konfigurationen zwischen Instanzen synchronisiert?
- [ ] Braucht der CLI-Client ebenfalls Zugriff auf die Config-API?
