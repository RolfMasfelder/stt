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
