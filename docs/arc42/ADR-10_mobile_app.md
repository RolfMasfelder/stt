# ADR-10: Mobile App Technologiewahl

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** FA-10, FA-11, FA-12, Z-7

## Kontext

Es soll eine Mobile App entstehen, die:
- Audio über das Mikrofon aufnimmt
- Die Aufnahme an den STT-Server sendet
- Ergebnisse anzeigt
- Server-Verbindung konfigurierbar macht

Die App muss auf Smartphones laufen. Zielplattformen und Technologie sind noch offen.

## Optionen

| Option | Beschreibung | Pro | Contra |
|--------|-------------|-----|--------|
| **A: Flutter (Dart)** | Cross-Platform Framework von Google | Eine Codebase für iOS + Android, gute Performance, starkes Ökosystem | Google-Abhängigkeit, Dart weniger verbreitet |
| **B: React Native (TypeScript)** | Cross-Platform Framework von Meta | JS/TS-Ökosystem, große Community, viele Libraries | Meta-Abhängigkeit, Bridge-Overhead |
| **C: Kotlin Multiplatform** | JetBrains Cross-Platform | Nativer Code, kein Bridge-Overhead, EU-Firma (CZ) | Jüngeres Ökosystem, weniger Libraries |
| **D: Native (Kotlin + Swift)** | Separate native Apps | Beste Performance, voller Platform-Zugriff | Doppelter Entwicklungsaufwand |
| **E: PWA (Web-App)** | Progressive Web App | Eine Codebase, kein App-Store, HTTPS-basiert | Eingeschränkter Mikrofon-Zugriff, kein Hintergrund-Recording |

## Empfehlung

**Option A (Flutter) oder C (Kotlin Multiplatform)** für den Produktausbau.

### Argumente für Flutter:
- Breites Ökosystem für Audio-Recording
- Ein Codebase → schnellere Entwicklung als Einzelentwickler
- Gute HTTP-Client-Libraries (dio)
- Offline-First-Architektur gut umsetzbar
- Material Design out of the box

### Argumente für Kotlin Multiplatform:
- JetBrains als europäischer Anbieter (Tschechien)
- Kein Bridge-Overhead
- Kotlin/JVM-Know-how transferierbar
- Weniger Abhängigkeit von US-Firmen (Google, Meta)

## Entscheidung

Noch offen — abhängig von Iteration über Anforderungen.

## Konsequenzen

- Audio-Recording-Permissions müssen auf beiden Plattformen behandelt werden
- Sichere Speicherung von Auth-Tokens auf dem Gerät (Keystore/Keychain)
- Netzwerk-Error-Handling und Offline-Fähigkeit
- OAuth2 PKCE Flow muss im Mobile-Framework umgesetzt werden

## Offene Fragen

- [ ] Wird initial nur Android oder auch iOS unterstützt?
- [ ] Ist der Entwickler mit Flutter/Dart oder Kotlin vertraut?
- [ ] Soll die App über einen App-Store vertrieben werden?
- [ ] Wie wichtig ist Unabhängigkeit von US-Frameworks?
