# ADR-09: Deployment-Szenarien und EU-Hosting

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** QA-9, Z-14, RB-11, RB-21

## Kontext

Aus Datenschutzgründen (DSGVO) sollen ausschließlich europäische Dienstleister genutzt werden. US-Provider unterliegen dem CLOUD Act, der unabhängig vom Serverstandort Zugriff auf Daten ermöglicht. Das Schrems-II-Urteil (EuGH) hat Datentransfers in die USA erheblich erschwert.

Zusätzlich ergeben sich unterschiedliche Betriebsszenarien je nach Kundengruppe und Datenschutzanforderung.

## Deployment-Szenarien

### Szenario 1: InHouse (On-Premises)

**Zielgruppe:** Anwälte, Notare, Ärzte, Behörden — besonders datenschutzsensible Anwender, bei denen Daten das Haus nicht verlassen dürfen.

| Aspekt | Beschreibung |
|--------|-------------|
| **Betriebsort** | Lokale Hardware beim Kunden (Server, NAS, Workstation) |
| **Netzwerk** | Nur lokales Netzwerk (LAN), kein Internet-Zugang erforderlich |
| **Deployment** | Docker Compose auf einem einzelnen Host |
| **Datenfluss** | Alle Daten verbleiben auf der lokalen Hardware |
| **LLM** | LM Studio oder Ollama lokal installiert |
| **Multi-User** | Einzelnutzer oder wenige Nutzer (Kanzlei, Praxis) |
| **TLS** | Self-Signed-Zertifikate oder internes CA |
| **Identity Provider** | Optional (kann auch nur API-Key-basiert sein) |

### Szenario 2: Dedicated Hosting (Single-Tenant)

**Zielgruppe:** Unternehmen/Organisationen, die einen eigenen Server bei einem EU-Hoster betreiben. Ein Kunde = eine Serverinstanz. Kein Multi-Tenant.

| Aspekt | Beschreibung |
|--------|-------------|
| **Betriebsort** | Dedizierter Server bei EU-Hoster (Hetzner, IONOS, Netcup, OVH) |
| **Netzwerk** | Internet-Zugang, Clients verbinden sich über HTTPS |
| **Deployment** | Docker Compose auf einem dedizierten Server |
| **Datenfluss** | Daten auf dem dedizierten Server des Kunden |
| **LLM** | vLLM, Ollama oder LM Studio auf dem Server |
| **Multi-User** | Mehrere Nutzer einer Organisation, aber Single-Tenant |
| **TLS** | Let's Encrypt via Caddy |
| **Identity Provider** | Keycloak/Zitadel Self-Hosted oder externe OIDC-Anbindung |

### Szenario 3: SaaS (Multi-Tenant)

**Zielgruppe:** Breiter Markt — Kunden nutzen einen gemeinsam betriebenen Dienst. Multi-Tenant, Multi-User.

| Aspekt | Beschreibung |
|--------|-------------|
| **Betriebsort** | Kubernetes-Cluster bei EU-Hoster |
| **Netzwerk** | Internet, öffentliche API |
| **Deployment** | Kubernetes mit Helm Charts, horizontale Auto-Skalierung |
| **Datenfluss** | Mandantentrennung (Tenant Isolation) auf Daten- und Verarbeitungsebene |
| **LLM** | vLLM oder vergleichbar als skalierbare GPU-Workload |
| **Multi-User** | Multi-Tenant, Multi-User, rollenbasierte Zugriffskontrolle |
| **TLS** | Let's Encrypt via Ingress Controller |
| **Identity Provider** | Zentraler Keycloak/Zitadel, pro Tenant eigener Realm/Organisation |
| **Skalierung** | Horizontale Auto-Skalierung (HPA) basierend auf Request-Last und GPU-Auslastung |
| **Datenbank** | PostgreSQL mit Schema-per-Tenant oder Row-Level-Security |
| **Monitoring** | Prometheus + Grafana, Alerting |

### Übersicht der Szenarien

| Eigenschaft | InHouse | Dedicated | SaaS |
|-------------|---------|-----------|------|
| Daten verlassen das Haus | Nein | Ja (zum Hoster) | Ja (zum Hoster) |
| Multi-Tenant | Nein | Nein | Ja |
| Internet erforderlich | Nein | Ja | Ja |
| Deployment | Docker Compose | Docker Compose | Kubernetes |
| Skalierung | Vertikal | Vertikal | Horizontal (Auto) |
| Betriebsaufwand Kunde | Hoch | Mittel | Niedrig |
| AV-Vertrag nötig | Nein (eigene Daten) | Ja | Ja |

## Entscheidung — EU-Hosting (für Szenarien 2 und 3)

Alle Infrastruktur-Dienstleister müssen folgende Kriterien erfüllen:

1. **Firmensitz in der EU/EWR oder Schweiz**
2. **Rechenzentren in der EU/EWR**
3. **Keine Unterordnung unter US-Recht** (kein US-Mutterkonzern)
4. **AV-Vertrag (Art. 28 DSGVO)** muss angeboten werden

### Evaluierte Anbieter (Beispiele)

| Kategorie | Anbieter | Land | Bemerkung |
|-----------|----------|------|-----------|
| **IaaS / VPS** | Hetzner | DE | Gutes Preis-Leistungs-Verhältnis, DE/FI Rechenzentren |
| **IaaS / VPS** | IONOS | DE | 1&1-Tochter, DE Rechenzentren |
| **IaaS / VPS** | Netcup | DE | Günstige Root-Server, DE Rechenzentren |
| **IaaS / VPS** | OVHcloud | FR | Großer EU-Provider, FR/DE Rechenzentren |
| **Object Storage** | IONOS S3 | DE | S3-kompatibel, DE Rechenzentren |
| **Object Storage** | OVH Object Storage | FR | S3-kompatibel |
| **Object Storage** | Wasabi EU | NL | S3-kompatibel, aber: US-Mutterkonzern → prüfen! |
| **Identity Provider** | Zitadel Cloud | CH | OIDC, Schweizer Hosting |
| **DNS / CDN** | bunny.net | SI | Europäisches CDN mit DSGVO-Fokus |
| **Kubernetes** | Hetzner K8s | DE | Managed Kubernetes, DE Rechenzentren |
| **Kubernetes** | IONOS K8s | DE | Managed Kubernetes |
| **Kubernetes** | OVH Managed K8s | FR | Managed Kubernetes |

### Ausgeschlossene Anbieter

- AWS, Azure, Google Cloud — US-Mutterkonzern, CLOUD Act
- Cloudflare — US-basiert
- DigitalOcean — US-basiert

## Begründung

- Drei Szenarien decken den gesamten Markt ab: von höchster Datensensibilität bis Massenmarkt
- InHouse-Szenario erforderlich für Berufsgeheimnisträger (§ 203 StGB: Anwälte, Ärzte, Notare)
- Dedicated Hosting für Kunden, die keinen eigenen Server betreiben wollen/können
- SaaS für Skalierung und breiten Marktzugang
- DSGVO Art. 44-49: Datentransfer in Drittstaaten nur unter strengen Bedingungen
- Schrems-II (EuGH C-311/18): Privacy Shield ungültig, SCCs allein oft nicht ausreichend
- CLOUD Act: US-Behörden können Zugriff auf Daten bei US-Unternehmen erzwingen

## Konsequenzen

- Deployment muss für alle drei Szenarien funktionieren (Docker Compose + Kubernetes)
- Konfiguration muss szenario-agnostisch sein (gleiche App, unterschiedliches Deployment)
- InHouse-Modus erfordert Offline-Fähigkeit (keine externen Dienste zur Laufzeit)
- SaaS erfordert Multi-Tenancy-Architektur und Kubernetes-Konfiguration
- AV-Verträge müssen für Szenarien 2 und 3 abgeschlossen und dokumentiert werden

## Offene Fragen

- [ ] Welcher Hosting-Anbieter wird für Szenario 2 und 3 gewählt?
- [ ] Managed Kubernetes oder Self-Managed?
- [ ] Wie werden InHouse-Installationen aktualisiert (Air-Gap-Updates)?
- [ ] Ist Wasabi EU trotz US-Mutterkonzern akzeptabel?
- [ ] GPU-Verfügbarkeit bei EU-Hostern (für Whisper + pyannote)?
