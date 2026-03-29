## Startmenü‑Übersicht
- **Allgemein**: Windows 11 verändert das Startmenü ständig; neue Funktionen werden stufenweise ausgerollt (z. B. neues „Start“ im November).
- **Anpassbarkeit**: Kacheln sind weg, stattdessen normale Icons in angehefteten Bereichen und Kategorien. Empfohlene Einstellungen: Alle Apps anzeigen, Empfehlungen abschalten, Widgets deaktivieren.
- **Registrierungs‑Hacks**: Manuell neue Startmenü‑Schalter setzen (Registry‑Keys) oder das Feature über die Settings-App aktivieren/deaktivieren.

## Taskleiste‑Anpassungen
- **Position**: Standard unten; seit Windows 11 können Seitenleisten‑Taskleisten auf 2. Monitoren angezeigt werden.
- **Icon‑Anzeige**: Nur aktuelle Fenster anzeigen lassen, Beschriftungen ein-/ausblenden (Windows 10‑Stil).
- **Verhalten**: Auf Hover anstatt Klick öffnen möglich, „Alle Apps“‑Button entfernen.

## Suche und Websuche
- **Desktop‑Suche**: Schnell über Windows‑Taste tippen; optional Websuche deaktivieren oder andere Provider wählen (z. B. Google).
- **Einstellungen**: `Start > Einstellungen > Suche` → „Websuche aktivieren/deaktivieren“, Bing‑App deinstallieren.

## Explorer‑Erweiterungen und Kontextmenüs
- **Dateiendungen anzeigen**: In den Explorer‑Optionen (Darstellungs‑/Ordner‑Optionen) ein-/ausblenden.
- **Versteckte Dateien**: Einmalige Option in Explorer, nicht im Settings‑App.
- **Kontextmenü‑Latenz**: Kann durch Hintergrund‑Dienste (z. B. Microsoft 365‑Sync) verlängert werden; Schalter zum klassischen Kontextmenü per Registry.

## Widgets & Widget‑Bot
- **Widget‑Board**: Eingeschränkte Auswahl, Newsfeed kann automatisch wieder aktiviert werden.
- **Entfernen**: PowerShell‑Skript zur Deinstallation (siehe Show Notes).

## Tastenkombinationen & Hotkeys
- **Standard**: Win L (Sperren), Strg+Shift+V (Plaintext einfügen).
- **Fenster‑Management**: Win ←/→ (linke/rechte Hälfte), Win ↑/↓ (obere/untere Hälfte), Snap‑Assist.
- **Virtuelle Desktops**: Alt+Tab, Win+Ctrl+↑/↓ (wechseln), Win+Ctrl+Mausklick (Fenster verschieben).

## PowerToys & Open Shell
- **PowerToys**: Sammlung von Tools (Color Picker, Keyboard Manager, PowerRename, etc.).
- **Open Shell**: Alternative Startmenü‑Ersetzung mit Windows 7‑Stil; kann in den Settings deaktiviert werden.

## System‑Features und Management‑Tools
- **Feature‑Verwaltung**: `Win+X` → „Windows‑Features verwalten“ (Hyper‑V, Sandbox).
- **Autoruns & Process Monitor**: Sysinternals‑Tools zur Analyse von Autostart‑Punkten und Laufzeitaktivitäten.

## Datenschutz‑Einstellungen (Telemetrie)
- **Diag‑Track / Telemetry**: Deaktivieren via `services.msc` oder PowerShell (`Set-ItemProperty`).
- **BSP‑Empfehlung**: E‑TV‑Sessions & Diag‑Track ausschalten; Windows Update muss jedoch aktiv bleiben.

## Sonstige Hinweise
- **Systemsteuerung**: Noch verfügbar, aber meist über Settings ersetzt.
- **Sound‑Einstellungen**: Für spezifische Profile weiterhin in der klassischen Systemsteuerung.
- **Widget‑Bot entfernen**: PowerShell‑Befehl aus Artikel; keine UI‑Option.

---
