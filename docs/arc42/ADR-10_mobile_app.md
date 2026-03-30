# ADR-10: Mobile App Technologiewahl

**Status:** Akzeptiert
**Datum:** 2026-03-30
**Bezug:** FA-10, FA-11, FA-12, FA-20, FA-21, FA-22, FA-23, Z-7, RB-14

## Kontext

Es soll eine Mobile App entstehen, die:
- Audio über das Mikrofon aufnimmt
- Die Aufnahme an den STT-Server sendet
- Ergebnisse anzeigt und speichert
- Server-Verbindung konfigurierbar macht
- Einen visuellen Status (HAL-9000-Auge) in drei Farben darstellt
- Konfiguration für Verarbeitung, Authentifizierung und Ablageorte bietet

**Zielplattformen:** Android und iOS (beide Plattformen gleichberechtigt).
**Komplexität:** Gering bis mittel — primär Statusanzeige, Aufnahme, Konfiguration, Server-Kommunikation. Keine komplexe lokale Datenverarbeitung.

## Bewertungskriterien

| Kriterium | Gewicht | Begründung |
|-----------|---------|------------|
| Cross-Platform (eine Codebase) | Hoch | Einzelentwickler, kein doppelter Aufwand |
| Audio-Recording | Hoch | Kernfunktion der App |
| OAuth2 PKCE Support | Hoch | Authentifizierung (ADR-07) |
| Animations / Custom UI | Mittel | HAL-9000-Auge mit Glow-Effekt und Farbübergängen |
| Secure Storage (Keystore/Keychain) | Hoch | Sichere Credential-Speicherung (RB-15) |
| Push Notifications | Mittel | Benachrichtigung bei Verarbeitungsende |
| HTTP-Client | Hoch | REST-API-Kommunikation, Multipart-Upload |
| Ökosystem-Reife | Mittel | Verfügbarkeit von Libraries, Community |
| EU-Anbieter-Unabhängigkeit | Niedrig | Nice-to-have, kein K.O.-Kriterium |
| Lernkurve für Einzelentwickler | Hoch | Python/Django-Background, keine Mobile-Erfahrung |

## Optionen

| Option | Beschreibung | Pro | Contra |
|--------|-------------|-----|--------|
| **A: Flutter (Dart)** | Cross-Platform Framework von Google | Eine Codebase, sehr gute Custom-UI/Animation-Fähigkeiten (ideal für HAL-Auge), ausgereiftes Audio-Ökosystem (`record`, `just_audio`), starkes HTTP-Ecosystem (`dio`), `flutter_secure_storage` für Keystore/Keychain, großes Ökosystem, Material Design | Google-Abhängigkeit, Dart als neue Sprache zu lernen |
| **B: React Native (TypeScript)** | Cross-Platform Framework von Meta | JS/TS-Ökosystem, große Community, viele Libraries | Meta-Abhängigkeit, Bridge-Overhead bei Animationen, weniger flüssige Custom-Animationen als Flutter |
| **C: Kotlin Multiplatform (KMP)** | JetBrains Cross-Platform | Nativer Code, kein Bridge-Overhead, EU-Firma (Tschechien), Kotlin-Syntax nahe Python | Jüngeres Ökosystem, weniger Audio-Libraries, UI-Sharing (Compose Multiplatform) noch weniger ausgereift |
| **D: Native (Kotlin + Swift)** | Separate native Apps | Beste Performance, voller Plattform-Zugriff | Doppelter Entwicklungsaufwand — als Einzelentwickler nicht tragbar |
| **E: PWA (Web-App)** | Progressive Web App | Eine Codebase, kein App-Store, HTTPS-basiert | Eingeschränkter Mikrofon-Zugriff, kein zuverlässiges Hintergrund-Recording, kein sicherer Keystore-Zugriff |

## Bewertungsmatrix

| Kriterium | Flutter | React Native | KMP | Native | PWA |
|-----------|---------|-------------|-----|--------|-----|
| Cross-Platform | ✅ | ✅ | ✅ | ❌ | ✅ |
| Audio-Recording | ✅ ausgereift | ✅ | ⚠️ weniger Libraries | ✅ | ⚠️ eingeschränkt |
| OAuth2 PKCE | ✅ (`flutter_appauth`) | ✅ | ✅ | ✅ | ⚠️ |
| Custom Animations (HAL-Auge) | ✅ exzellent | ⚠️ Bridge-Overhead | ⚠️ Compose MP noch jung | ✅ | ✅ (CSS/Canvas) |
| Secure Storage | ✅ (`flutter_secure_storage`) | ✅ | ✅ | ✅ | ❌ kein Keystore |
| Push Notifications | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| HTTP-Client | ✅ (`dio`) | ✅ (`axios`) | ✅ (`ktor`) | ✅ | ✅ (`fetch`) |
| Lernkurve | Mittel (Dart) | Mittel (JS/TS) | Mittel-Hoch (Kotlin) | Hoch (2 Sprachen) | Niedrig (Web) |

## Empfehlung

**Option A: Flutter** als primäre Empfehlung.

### Begründung:

1. **HAL-9000-Auge:** Flutter hat die beste Custom-Rendering-Engine (Skia/Impeller) — animierte Glow-Effekte, Farbübergänge und kreisförmige UI-Elemente sind Flutters Stärke
2. **Audio-Recording:** Ausgereiftes Ökosystem (`record`-Package, `audio_session`)
3. **Eine Codebase:** Als Einzelentwickler ist doppelter Aufwand nicht tragbar
4. **Geringe App-Komplexität:** Für einfache Apps (Status, Aufnahme, Konfiguration, Upload) ist Flutter ideal — der Overhead eines nativen Frameworks lohnt nicht
5. **Secure Storage:** `flutter_secure_storage` nutzt automatisch Android Keystore / iOS Keychain
6. **OAuth2 PKCE:** `flutter_appauth` bietet native PKCE-Unterstützung
7. **HTTP:** `dio` bietet Multipart-Upload, Interceptors, Progress-Callbacks

### KMP als Alternative:
Falls die Abhängigkeit von Google ein Problem darstellt, ist KMP die zweitbeste Option. Das UI-Sharing über Compose Multiplatform ist allerdings noch weniger ausgereift als Flutter, insbesondere für Custom-Animationen.

## Entscheidung

**Flutter (Option A).**

Begründung: Da eine definierte REST-API-Schnittstelle zum Backend besteht (OpenAPI-Spezifikation), ist die Wahl des Mobile-Frameworks entkoppelt vom Backend. Eine spätere Neuentwicklung mit einem anderen Framework (z. B. KMP) ist jederzeit möglich, ohne das Backend zu verändern. Flutter bietet für den aktuellen Anwendungsfall (geringe Komplexität, Custom-UI für HAL-Auge, Audio-Recording) das beste Gesamtpaket.

## Konsequenzen

- Audio-Recording-Permissions müssen auf beiden Plattformen behandelt werden
- Sichere Speicherung von Auth-Tokens auf dem Gerät (Keystore/Keychain)
- Netzwerk-Error-Handling und Offline-Fähigkeit
- OAuth2 PKCE Flow muss in Flutter umgesetzt werden (`flutter_appauth`)
- HAL-9000-Auge erfordert Custom-Painting/Animation-Fähigkeiten (Flutter `CustomPainter` / `AnimationController`)
- Push-Notification-Integration für Verarbeitungsstatus
- Dart als Programmiersprache zu erlernen (Lernkurve einplanen)
- Späterer Framework-Wechsel (z. B. KMP) möglich dank definierter Backend-API
- **App-Store-Vertrieb:** Veröffentlichung über Google Play Store und Apple App Store erforderlich — dafür nötig: Google Play Developer Account (einmalig 25 USD), Apple Developer Program (99 USD/Jahr), Einhaltung der jeweiligen Store-Richtlinien (Datenschutz-Labels, App-Review-Prozess)

### Risiko: iOS-Testbarkeit

Derzeit stehen nur Android-Geräte zum Testen zur Verfügung. iOS-Tests müssen über Alternativen abgedeckt werden:
- **iOS-Simulator** (Xcode auf macOS) für funktionale Tests
- **CI/CD-Dienste** mit macOS-Runnern (z. B. GitHub Actions macOS, Codemagic)
- **Beschaffung eines iOS-Testgeräts** zu einem späteren Zeitpunkt
- Flutter-Cross-Platform-Garantie reduziert das Risiko: gleicher Code, plattformspezifische Anpassungen primär bei Permissions und Keychain-Zugriff

## Offene Fragen

- [x] ~~Wird initial nur Android oder auch iOS unterstützt?~~ → Beide Plattformen (RB-14)
- [x] ~~Ist der Entwickler mit Flutter/Dart oder Kotlin vertraut?~~ → Nein, Dart/Flutter-Lernkurve einplanen
- [x] ~~Wie wichtig ist Unabhängigkeit von US-Frameworks?~~ → Kein K.O.-Kriterium; späterer Wechsel dank API-Entkopplung möglich
- [x] ~~Soll die App über einen App-Store vertrieben werden?~~ → Ja, Vertrieb über Google Play Store und Apple App Store. Ohne App-Store-Verfügbarkeit wirkt die App unprofessionell; Zielgruppe sind technisch nicht versierte Anwender, Sideloading kommt nicht in Frage
- [x] ~~iOS-Testgerät beschaffen oder rein über Simulator/CI testen?~~ → Zunächst über iOS-Simulator (Xcode) und CI mit macOS-Runnern. Testgerät-Beschaffung bei Bedarf später
