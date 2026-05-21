# TODO – Ollama-Integration & offene Punkte

## Stand der Ollama-Einbindung

### Bereits erledigt

- [x] **Docker-Compose Service**: `ollama` Service definiert (Image `ollama/ollama:latest`, Port 11434, Volume `ollama_data`, Netzwerk `stt-network`). Läuft unter eigenem Profil `ollama`.
- [x] **Konfiguration via Umgebungsvariablen**: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TIMEOUT` in `stt-server` und `stt-worker` durchgereicht.
- [x] **OpenAI-kompatibler HTTP-Client** (`src/stt/summarize.py`): Kommuniziert über `/v1/chat/completions` – funktioniert mit Ollama und LM Studio gleichermaßen.
- [x] **Config-Defaults** (`src/stt/config.py`): Default `base_url=http://localhost:11434`, Model `mistral`.
- [x] **.env.example**: Dokumentiert alle Ollama-Varianten (lokal Docker, Remote).
- [x] **.env**: Zeigt aktuell auf `http://192.168.178.80:11434` (Ollama auf Remote-Rechner).
- [x] **Helm ConfigMap**: LLM-Konfiguration in `k8s/helm/stt/templates/configmap.yaml` (bedingt, nur wenn `llm.baseUrl` gesetzt).
- [x] **Helm Values**: `llm.baseUrl` und `llm.model` in `values.yaml` vorbereitet (aktuell leer).
- [x] **Testabdeckung** (`tests/test_summarize.py`): Vollständige Tests für Zusammenfassung, Strukturierung, Fehlerbehandlung, Pipeline.

---

## Offene Punkte

### 1. Ollama Docker-Profil (separater Betrieb)

Ollama läuft auf einem **Remote-Rechner** (192.168.178.80), nicht im selben Compose-Stack.
Das separate Profil `ollama` ist daher korrekt und bleibt bestehen.

- [x] Entscheidung: Ollama läuft **extern** (Remote-Rechner), nicht im `production`-Profil.
- [x] Separates Profil `ollama` existiert bereits in `docker-compose.yml`.
- [x] Health-Check: `GET /api/tags` als readiness/liveness-Probe definiert (in `k8s/base/ollama.yaml`).
- [x] Ollama wird via **k3s** auf dem Remote-Rechner (192.168.178.80) provisioniert (`k8s/base/ollama.yaml`).

### 1a. Ollama-Schnittstelle dokumentieren

Von Ollama wird **ein** Endpunkt genutzt: `POST /v1/chat/completions` (OpenAI-kompatibel).
Das gehört **nicht** in die bestehende `openapi.json` – diese beschreibt ausschließlich die
STT-Server-API (unsere eigene Schnittstelle). Ollama ist eine Fremd-API, die wir als Client
konsumieren. Dokumentation erfolgt in arc42 (Kontextabgrenzung, Bausteinsicht).

- [x] `docs/anwendungsuebersicht.md`: S3-Schnittstellentabelle aktualisiert (tatsächlich genutzter Endpunkt, Health-Check).
- [x] `docs/anwendungsuebersicht.md`: Infrastruktur-Abschnitt mit Netzwerk-Architektur, Abhängigkeiten und Konfigurationsreferenz.
- [x] `docs/arc42/03_kontextabgrenzung.md`: Ollama-Schnittstelle (`POST /v1/chat/completions`) mit Request/Response-Format dokumentieren.

### 2. GPU-Unterstützung für Ollama *(zurückgestellt – keine GPU verfügbar)*

> Derzeit steht kein Rechner mit geeigneter GPU zur Verfügung. Vorbereitung ohne
> verifizierbare Tests wird zurückgestellt bis Hardware vorhanden ist.

- [ ] Docker-Compose: `deploy.resources.reservations.devices` für NVIDIA GPU hinzufügen (optional, mit Kommentar).
- [ ] Kubernetes: GPU `nodeSelector` und `tolerations` in Helm Values für Ollama vorbereiten.
- [ ] Dokumentation: Welche GPU-Treiber (NVIDIA Container Toolkit) benötigt werden.

### 3. Modell-Provisionierung (Model Pull)

`ollama pull <model>` lädt ein **ML-Modell** (nicht das Docker-Image) in das Volume
`/root/.ollama`. Das passiert inkrementell: ist das Modell bereits vorhanden, wird nur
auf Updates geprüft. Bei persistentem Volume (`ollama_data`) überlebt das Modell
Container-Neustarts – ein erneuter Pull ist nur bei Modell-Updates nötig.

```bash
# Einmalig nach erstem Start:
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull mistral
```

- [x] Dokumentation der manuellen Schritte (s.o.) in README.md.
- [ ] Optional: Init-Container oder Entrypoint-Script für automatischen Pull wenn Modell fehlt.

### 4. Kubernetes Ollama-Deployment

- [x] Kustomize-Manifest erstellt: `k8s/base/ollama.yaml` (Deployment, Service, PVC, Ingress).
- [x] `k8s/base/kustomization.yaml`: `ollama.yaml` als Resource hinzugefügt.
- [x] `values-k3s.yaml`: `llm.baseUrl=http://ollama:11434`, `llm.model=mistral` gesetzt.
- [x] PersistentVolumeClaim `ollama-data` (20Gi, local-path) für Modell-Daten.
- [x] Ingress: `ollama.stt.local` via bestehenden nginx-Ingress-Controller.
- [x] Health-Probes: readiness + liveness via `GET /api/tags`.
- [x] NetworkPolicy: Egress-Regel für ingress-nginx → stt-Namespace (`networkpolicy-ingress-egress-stt.yaml`).
- [x] Docker-Compose: `extra_hosts` für `ollama.stt.local` in `stt-server` und `stt-worker`.
- [x] End-to-End-Test: Docker-Container → Ollama via Ingress → Mistral verifiziert.

#### Deployment-Anleitung

```bash
# 1. Kustomize-Ressourcen deployen (Namespace stt muss existieren)
kubectl apply -k k8s/base/

# 2. Warten bis Ollama-Pod läuft
kubectl -n stt rollout status deployment/ollama

# 3. Modell einmalig laden (nur beim ersten Mal nötig)
kubectl -n stt exec deployment/ollama -- ollama pull mistral

# 4. Helm-Deployment aktualisieren (stt-server bekommt LLM_BASE_URL)
helm upgrade stt k8s/helm/stt/ -n stt -f k8s/helm/values-k3s.yaml

# 5. DNS: ollama.stt.local auf LoadBalancer-IP auflösen
# Auf allen Clients die Ollama nutzen wollen (z.B. /etc/hosts):
# 192.168.178.200  ollama.stt.local
```

**Netzwerk-Architektur:**
```
MetalLB LoadBalancer: 192.168.178.200 (Ports 80/443)
  └─ ingress-nginx (Namespace ingress-nginx, aus eRechnung-Projekt)
       ├─ erechnung.local      → eRechnung-App
       ├─ minio.stt.local      → MinIO-Console (:9001)
       ├─ stt.local             → STT-Server (:8090)
       └─ ollama.stt.local      → Ollama (:11434)
```

**Zugriff aus Docker-Compose** (lokaler Entwicklungsrechner):
```bash
# .env → Ollama via Ingress (MetalLB-IP, Port 80):
LLM_BASE_URL=http://ollama.stt.local
# DNS-Eintrag nötig: 192.168.178.200  ollama.stt.local
# Kein firewall-cmd nötig – Port 80/443 sind bereits offen (MetalLB).
```

**Zugriff aus k8s** (im selben Cluster):
```bash
# values-k3s.yaml → Cluster-interner Service (kein Ingress nötig):
LLM_BASE_URL=http://ollama:11434
# Oder FQDN: http://ollama.stt.svc.cluster.local:11434
```

### 5. Netzwerk-Konfiguration (On-Premises / Remote)

MetalLB (konfiguriert in `eRechnung_Django_App/infra/k8s/k3s/metallb-lan-config.yaml`)
stellt den IP-Pool `192.168.178.200-210` bereit. Der ingress-nginx-Controller bekommt
die erste IP (`192.168.178.200`) und leitet nach Hostname weiter. Ports 80/443 sind
bereits via MetalLB erreichbar – **keine firewall-cmd-Regel für Ollama nötig**.

- [x] Szenarien dokumentiert (siehe Abschnitt 4 oben):
  - **k8s-intern**: `http://ollama:11434` (ClusterIP Service, direkt)
  - **LAN via Ingress**: `http://ollama.stt.local` (MetalLB 192.168.178.200:80)
  - **Cloud/Dedicated**: `https://llama.example.com` (TLS via cert-manager, später)
- [x] DNS-Eintrag `ollama.stt.local → 192.168.178.200` auf Entwicklungsrechner konfiguriert (`/etc/hosts`).
- [x] Ingress-Timeout auf 3600s gesetzt (nginx-Annotations in `ollama.yaml`).
- [x] Prüfen ob Timeout-Werte (`LLM_TIMEOUT=3600`) für große Modelle ausreichen.

### 6. Doku aktualisieren (Ollama als Produktion, LM Studio als Entwicklungsvariante)

> LM Studio bleibt in der arc42-Doku als Entwicklungs-/Prompt-Tuning-Variante erhalten.
> Ollama wird als produktive Entscheidung eingepflegt.

- [x] `README.md`: Architektur-Diagramm aktualisieren – Ollama als primäres LLM-Backend, LM Studio als optionale Dev-Alternative.
- [x] `README.md`: Voraussetzungen: Ollama (Produktion) oder LM Studio (Entwicklung).
- [x] `README.md`: Beschreibung der Services aktualisieren.
- [x] `docs/arc42/02_randbedingungen.md`: Ollama als produktive Wahl, LM Studio als Dev-Option erwähnen.
- [x] `docs/arc42/03_kontextabgrenzung.md`: Kontextdiagramm um Ollama (:11434) ergänzen.
- [x] `docs/arc42/04_loesungsstrategie.md`: Ollama als gewählte Technologie, LM Studio als Alternative beibehalten.
- [x] `docs/arc42/05_bausteinsicht.md`: Ollama als primäres Backend eintragen.
- [x] `docs/arc42/06_laufzeitsicht.md`: Sequenzdiagramme um Ollama ergänzen.
- [x] `docs/arc42/07_verteilungssicht.md`: Verteilungsdiagramm mit Ollama-Container aktualisieren.
- [x] `docs/arc42/08_entscheidungen.md`: ADR-5 ergänzen: Entscheidung für Ollama im produktiven Betrieb, LM Studio bleibt für Entwicklung.
- [x] `docs/arc42/ADR-08_verschluesselung.md`: Ollama-Kommunikation ergänzen.
- [x] `docker_usage.md`: Ollama-Nutzung ergänzen.

### 7. Resilience & Monitoring

- [x] Retry-Logik in `summarize.py`: Bei temporären Ollama-Fehlern (503, Timeout, ConnectionError) 3x mit Backoff wiederholen.
- [x] Health-Endpoint im Server, der LLM-Erreichbarkeit prüft (`GET /health` → Ollama `/api/tags`).
- [ ] Metriken: LLM-Antwortzeiten, Fehlerrate, Modell-Verfügbarkeit loggen.
- [x] Circuit-Breaker: Bei anhaltenden LLM-Fehlern graceful degradieren (Transkription ohne Zusammenfassung).

### 8. Sicherheit

- [ ] Ollama-Port (11434) nur im internen Netzwerk exponieren, nicht öffentlich.
- [ ] Bei Remote-Betrieb: TLS zwischen `stt-server` und Ollama erzwingen (oder VPN/Wireguard).
- [ ] Prüfen ob Ollama Authentication-Header unterstützt (aktuell: keine Auth).
- [ ] Network-Policy in Kubernetes: Nur `stt-server` und `stt-worker` dürfen Ollama erreichen.

### 9. Weitere offene Punkte (nicht Ollama-spezifisch)

- [x] `.env` ist in `.gitignore` eingetragen und wird nicht getrackt.
- [x] `openapi.json` validieren und aktualisieren: Diff gegen Live-API durchgeführt, 3 Felder nachgezogen (`HealthResponse.llm`, `ProcessResponse.structured_text`/`summary` nullable).
- [x] `HF_STT_TOKEN` rotieren falls er jemals committed wurde (git-history geprüft: kein echter Token-Wert in keinem Commit – nur der Variablenname in Konfig-Dateien).
- [x] Flutter-App: API-Anbindung an `/v1/process` – **obsolet**. Flutter nutzt korrekt `/v1/jobs` (async Job-Queue). Kein Handlungsbedarf.
- [x] `language`-Parameter end-to-end implementiert: ML-Service (`faster-whisper`), `transcribe.py`/`diarize.py`, `Job`-Modell (`whisper_language`), Migration `0009`, Views, Tasks, Flutter `upload.dart`.
- [x] LLM-Ausgabesprache: `process_transcript()` hängt Sprachanweisung an System-Prompts an – Zusammenfassung/Strukturierung erscheint in der gewählten Sprache (nicht nur Transkription).
- [x] Flutter-Tests verbessern: `UploadService` mit gemocktem HTTP-Client (`test/upload_service_test.dart`), `ResultScreen`-Widget-Tests inkl. aller Tab-Kombinationen (`test/result_screen_test.dart`), `RecordingHistoryService`-Persistenz (`test/recording_history_test.dart`), `ProcessingConfigService`-Tests mit Serialisierungsround-trips und allen Bool-Kombinationen (`test/processing_config_service_test.dart`), Settings-Toggle-E2E in `test/e2e_test.dart`.
- [x] CI/CD: GitHub Actions Workflow für automatisierte Tests und Container-Build (`backend-test.yml`, `backend-quality.yml`, `backend-security.yml`, `docker-build.yml`, `flutter-ci.yml`, `ml-ci.yml` für ML-Microservice-Lint).
- [ ] SBOM-Dateien (`sbom/`) aktuell halten.
