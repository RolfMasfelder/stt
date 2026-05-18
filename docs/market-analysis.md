# Marktanalyse – Wettbewerber & Positionierung

Stand: Mai 2026

---

## Plaud (plaud.ai)

**Kategorie:** KI-gestützter Audio-Recorder mit proprietärer Hardware + Cloud-Dienst
**Nutzer:** >2 Millionen Professionals weltweit
**Quellen:**
- Produktseite: https://www.plaud.ai/
- Preisvergleich: https://support.plaud.ai/hc/en-us/articles/50742099278617-Comparison
- AI Membership FAQ: https://support.plaud.ai/hc/en-us/articles/57724862694937-Plaud-AI-Membership-FAQ

### Hardware (Einmalige Anschaffungskosten)

| Gerät | Preis (USD) | Besonderheit |
|---|---|---|
| Plaud Note | $159 | Smartphone-Clip, Calls + Meetings |
| Plaud NotePin | $159 | Wearable Clip-On |
| Plaud NotePin S | $179 | Wearable + 4 Zubehörteile |
| Plaud Note Pro | $189 | 4 MEMS-Mikrofone, größere Räume |

Hardware-Kauf ist der primäre Lock-in: Nutzer investieren einmalig in das Gerät
und bleiben dann im Plaud-Ökosystem.

### Software – AI Membership (Abonnement)

| Plan | Monatlich | Jährlich (pro Monat) | Transkription | Zielgruppe |
|---|---|---|---|---|
| Starter | kostenlos | — | 300 min/Monat | Einsteiger, inklusive bei Gerätekauf |
| Pro | $17.99 | $8.33 (54% Ersparnis) | 1.200 min/Monat (20h) | Berufstätige mit regelmäßigen Meetings |
| Unlimited | $29.99 | $20.00 (33% Ersparnis) | bis 24h/Tag | Ärzte, Anwälte, Journalisten, Vertrieb |
| Team | $28/User/Monat | $20/User/Monat (Intro bis Aug 2026) | bis 24h/Tag + Admin-Console | Teams mit zentraler Verwaltung |

**Hinweis:** Team-Plan steigt nach Aug 2026 auf $35/User/Monat (monatlich) bzw.
$25/User/Monat (jährlich).

Nicht genutzte Transkriptionsminuten verfallen monatlich (kein Rollover).
Top-up möglich: 600 / 3.000 / 6.000 Minuten als Einmalkauf.

### Was Plaud bietet

- Transkription in 112 Sprachen mit Sprecheridentifikation
- Multidimensionale Zusammenfassungen + 10.000+ professionelle Templates
- "Ask Plaud" – natürlichsprachliche Suche über alle Aufnahmen
- AutoFlow – automatische Folgeaufgaben, Action Items, Exporte
- Aktuelle KI-Modelle: GPT-5, Gemini 3 Pro, Claude Sonnet (laufend aktualisiert)
- Private Cloud Sync (verschlüsselt, cross-device)
- Compliance: ISO 27001, ISO 27701, EN18031, DSGVO, HIPAA, SOC 2

---

## Positionierung von STT gegenüber Plaud

### Stärken von STT (Alleinstellungsmerkmale)

| Merkmal | Plaud | STT |
|---|---|---|
| Hardware erforderlich | Ja ($159–$189) | Nein – handelsübliches Smartphone |
| Datenverarbeitung | Cloud (USA) | Lokal, keine Cloud |
| Datenschutz | Verschlüsselt, aber auf Plaud-Servern | Daten verlassen niemals das eigene Netz |
| DSGVO Art. 17 (Löschrecht) | Abhängig von Plaud | Vollständige Kontrolle |
| Geeignet für NDA-Gespräche | Fraglich | Ja |
| Kein Abo erforderlich | Nein (Starter nur 300 min/Monat) | Ja (self-hosted, unbegrenzt) |
| Offline-fähig | Nein | Ja |
| Open Source | Nein | Ja (AGPL-3.0 geplant) |

### Zielgruppen mit besonderem Bedarf an lokalem Betrieb

- **Anwaltskanzleien** – Mandantengespräche, Berufsgeheimnis
- **Arztpraxen / Kliniken** – DSGVO, § 203 StGB (Schweigepflicht), HIPAA
- **Unternehmensberatungen** – NDA-gebundene Projektkommunikation
- **Behörden / öffentliche Verwaltung** – VS-NfD, IT-Grundschutz
- **Journalisten** – Quellenschutz
- **Forschungseinrichtungen** – Vertrauliche Studiendaten

### Schwächen von STT gegenüber Plaud

- Kein eigenes Aufnahmegerät / keine Hardware-Integration (bewusste Entscheidung)
- Keine 10.000+ Templates out-of-the-box
- Keine natürlichsprachliche Suche über alle Aufnahmen ("Ask Plaud"-Äquivalent)
- Keine automatische Modellaktualisierung (Nutzer verwaltet Ollama-Modelle selbst)
- Kleinere Community, kein 24h-Support

---

## Mögliches Pricing-Modell für STT

Basierend auf Plaud-Preisen und Positionierung:

| Tier | Preis | Inhalt |
|---|---|---|
| **Community (AGPL)** | kostenlos | Self-hosted, voller Funktionsumfang, AGPL-Pflichten |
| **Commercial Self-Hosted** | einmalig ~€299 oder ~€99/Jahr | Deployment ohne AGPL-Pflichten, E-Mail-Support |
| **Enterprise** | ab €999/Jahr | Multi-User, SLA, Custom-Deployment, Schulung |

Alternativ: Managed Hosting (wenn Hosting-Infrastruktur aufgebaut wird):
- ~$15–20/User/Monat (zwischen Plaud Starter und Pro positioniert, aber mit
  vollständiger Datenprivatsphäre als Hauptargument)
