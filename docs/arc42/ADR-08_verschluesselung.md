# ADR-08: Ende-zu-Ende-Verschlüsselung

**Status:** Vorgeschlagen
**Datum:** 2026-03-28
**Bezug:** QA-8, Z-13, RB-9

## Kontext

Audio-Aufnahmen und Transkripte enthalten personenbezogene Daten (Stimmen, gesprochene Inhalte). DSGVO Art. 32 verlangt angemessene technische Schutzmaßnahmen. Daten müssen sowohl bei der Übertragung als auch bei der Speicherung geschützt werden.

## Entscheidung

### Verschlüsselung im Transit

- TLS 1.3 für alle HTTP-Verbindungen (Client → Server, Server → LM Studio, Server → Storage)
- Reverse-Proxy (z. B. Caddy, Traefik) für TLS-Terminierung
- HSTS-Header zur Erzwingung von HTTPS
- Keine Ausnahmen für interne Kommunikation (Zero-Trust)

### Verschlüsselung at Rest

| Option | Beschreibung | Bewertung |
|--------|-------------|-----------|
| **A: Filesystem-Verschlüsselung (LUKS)** | Betriebssystem-Level, transparent | Einfach, schützt gegen physischen Zugriff |
| **B: Anwendungsebene (AES-256-GCM)** | Verschlüsselung vor dem Speichern | Maximaler Schutz, auch bei Storage-Kompromittierung |
| **C: Storage-seitig (S3 SSE)** | Verschlüsselung durch den Storage-Provider | Provider-abhängig, weniger Kontrolle |

### Empfehlung

**Kombination A + B:** Filesystem-Verschlüsselung als Baseline, anwendungsseitige Verschlüsselung für sensible Daten (Audio, Transkripte).

### Schlüsselverwaltung

- Verschlüsselungsschlüssel getrennt von Daten gespeichert
- Pro Nutzer/Organisation eigene Schlüssel (Key Isolation)
- Möglichkeit: HashiCorp Vault (Self-Hosted) oder Dateisystem-basiert mit restriktiven Berechtigungen

## Begründung

- DSGVO Art. 32 fordert Verschlüsselung als technische Schutzmaßnahme
- Audio-Daten sind biometrische Merkmale (besondere Kategorie, Art. 9)
- Zero-Trust erfordert Schutz auch gegen kompromittierte Infrastruktur
- TLS 1.3 bietet Forward Secrecy

## Konsequenzen

- TLS-Zertifikatsverwaltung erforderlich (Let's Encrypt für öffentliche Server)
- Performance-Overhead durch Verschlüsselung (akzeptabel)
- Schlüsselverlust = Datenverlust → Backup der Schlüssel kritisch
- Reverse-Proxy als zusätzliche Infrastruktur-Komponente

## Offene Fragen

- [x] ~~Welcher Reverse-Proxy?~~ → Caddy gewählt (automatisches Let's Encrypt, `Caddyfile` im Projekt)
- [ ] Wie wird die Schlüsselverwaltung in der ersten Version umgesetzt?
- [ ] Sind Audio-Aufnahmen als biometrische Daten (Art. 9) zu klassifizieren?
