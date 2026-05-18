# Docker-Nutzung

## Produktions-Stack starten

```bash
# Alle Container (stt-server, stt-worker, stt-ml, stt-ollama, db, caddy)
docker compose --profile production up -d

# Einzelnen Service neu starten
docker compose restart stt-server
```

## Ollama-Modell laden (einmalig nach erstem Start)

```bash
# Modell herunterladen (persistiert in Volume ollama_data)
docker compose exec stt-ollama ollama pull mistral

# Verfügbare Modelle anzeigen
docker compose exec stt-ollama ollama list
```

Das Modell überlebt Container-Neustarts dank des persistenten Volumes `ollama_data`.
Ein erneuter Pull ist nur bei Modell-Updates nötig.

## CLI nutzen

```bash
# Vollständige Pipeline (HTTPS via Caddy, Credentials aus .env)
docker compose --profile cli run --rm stt-cli python -m stt \
  data/audio/meeting.wav --diarize --process -o data/output/result.txt

# Caddy-Zertifikat einmalig abrufen (falls noch nicht vorhanden)
ssh rolf@192.168.178.80 \
  "docker exec stt-caddy cat /data/caddy/pki/authorities/local/root.crt" \
  > caddy-root.crt
```

Die Umgebungsvariablen (`STT_SERVER_URL`, `OAUTH2_CLIENT_ID`, `REQUESTS_CA_BUNDLE` etc.)
werden automatisch aus `.env` geladen (`env_file: .env` im `stt-cli`-Service).

## Tests ausführen

```bash
docker compose --profile test run --rm stt-test
```

## Deployment auf cirrus7-neu

```bash
# Build + Push + Pull + Restart (inkl. Caddy-Cert + OAuth2-Bootstrap)
./scripts/deploy-remote-docker.sh

# Nur Images bauen ohne Cache
./scripts/deploy-remote-docker.sh --no-cache
```

## Nützliche Befehle

```bash
# Logs aller Produktions-Container
docker compose --profile production logs -f

# Django-Migrations ausführen
docker compose exec stt-server python manage.py migrate

# Django-Shell
docker compose exec stt-server python manage.py shell

# Status prüfen
docker compose ps
```

---

## Flutter Web (lokales Browser-Testing)

Der Flutter-Web-Stack ermöglicht es, die mobile App im Browser zu testen ohne
natives Build. OAuth2 läuft via PKCE-Popup, Audio wird als Opus/WebM aufgenommen.

### Voraussetzungen (einmalig)

```bash
# OAuth2-Client anlegen (flutter-web-dev, PUBLIC, redirect http://localhost:5000/callback.html)
docker compose exec stt-server python manage.py create_web_oauth2_client

# Admin-Passwort setzen (falls noch nicht geschehen)
docker compose exec stt-server python manage.py changepassword admin
```

### Stack starten

```bash
# 1. Django-Server (HTTP, kein SSL-Redirect, COOP deaktiviert für OAuth2-Popup)
docker compose --profile production run -d --no-deps \
  -e DEBUG=true --name stt-server --service-ports stt-server

# 2. ML-Worker (verarbeitet Transkriptions-Jobs; eigener Cluster "ml")
docker run -d \
  --name stt-ml-worker \
  --network stt_stt-network \
  -e DATABASE_URL=postgres://stt:stt_dev@db:5432/stt \
  -e DJANGO_SETTINGS_MODULE=stt.settings \
  -e Q_CLUSTER_NAME=ml \
  -e DEBUG=true \
  192.168.178.80:5000/stt-server:latest \
  python manage.py qcluster

# 3. Flutter-Web-App (build + serve auf Port 5000)
docker compose --profile web-dev up -d flutter-web
# Warten bis "Serving build/web at http://0.0.0.0:5000" in den Logs erscheint:
docker compose --profile web-dev logs -f flutter-web
```

### App nutzen

1. Browser: http://localhost:5000
2. Einstellungen → Server-URL: `http://localhost:8090` → Client-ID: `flutter-web-dev` → **Anmelden**
3. Im Popup: Django-Admin-Login → **Autorisieren** → Popup schließt sich automatisch
4. Zurück auf Startseite: HAL-Auge antippen → Aufnahme starten → stoppen → **Hochladen**
5. "Wird verarbeitet..." — der ML-Worker transkribiert die Aufnahme (Dauer je nach Länge)
6. Nach Abschluss: **Ergebnis anzeigen** oder unter **Aufnahmen** (Uhr-Icon oben rechts)

### Aufräumen nach dem Test

```bash
docker rm -f stt-server stt-ml-worker
# flutter-web läuft weiter oder:
docker compose --profile web-dev stop flutter-web
```

### Architektur-Hinweise

**Zwei Worker-Cluster** — Django-Q2 trennt Aufgaben in zwei Cluster:
- `stt`-Cluster (`stt-worker`): Scheduled Tasks (tägliche Bereinigung etc.)
- `ml`-Cluster (`stt-ml-worker`): ML-Verarbeitung (Whisper, pyannote, Ollama)

Beide Cluster müssen denselben `name` in `Q_CLUSTER` verwenden (→ identischer
Signing-Salt/PREFIX), Routing erfolgt über `cluster_name`. Sonst: `BadSignature`
beim Task-Pickup. Konfiguration: `src/stt/settings.py` → `Q_CLUSTER_ML`.

**OAuth2-Popup auf Web** — Django setzt standardmäßig
`Cross-Origin-Opener-Policy: same-origin`, was `window.opener` im Popup kappt.
Deshalb: `SECURE_CROSS_ORIGIN_OPENER_POLICY = None` in `settings.py`.
Nur relevant für HTTP-Dev-Betrieb; in Produktion läuft alles same-origin via Caddy.

**Image neu bauen** nach Änderungen an `src/`:
```bash
docker compose build stt-server
# dann stt-server + stt-ml-worker neu starten (siehe oben)
```
