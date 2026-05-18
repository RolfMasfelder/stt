# 3. Kontextabgrenzung

## Fachlicher Kontext

```
                        ┌─────────────────────┐
                        │                     │
  Audio-Datei (.wav) ──►│    STT-System       │──► Transkript (.txt)
                        │                     │──► Sprecherzuordnung (.md)
                        │                     │──► Strukturierung (.md)
                        │                     │──► Zusammenfassung (.md)
                        │                     │
                        └─────────────────────┘
                                ▲
                                │
                          Nutzer (CLI)
```

Der Nutzer übergibt eine Audio-Datei per Kommandozeile. Das System liefert Text-Ergebnisse als Dateien oder auf stdout.

## Technischer Kontext

```
┌──────────────────┐   HTTPS/REST (via Caddy)   ┌──────────────────────────────┐
│  Workstation     │ ─────────────────────────► │  cirrus7-neu 192.168.178.80  │
│                  │                             │                              │
│  stt-cli         │  POST /v1/process           │  caddy (:443)                │
│  (CLI + Client)  │  ◄── JSON ──────────────── │    └─► stt-server (:8090)    │
│                  │                             │          ├─► stt-ml (:8091)  │
└──────────────────┘                             │          └─► ollama (:11434) │
                                                 │                              │
                                                 └──────────────────────────────┘
```

### Externe Schnittstellen

| Schnittstelle | Protokoll | Endpunkt | Beschreibung |
|---------------|-----------|----------|--------------|
| STT Server API | HTTPS/REST | `/v1/transcribe`, `/v1/diarize`, `/v1/process`, `/health` | Definiert in `openapi.json`. OAuth2 Client Credentials. |
| stt-ml (intern) | HTTP/REST | `POST /v1/transcribe` | Whisper-Transkription via faster-whisper |
| stt-ml (intern) | HTTP/REST | `POST /v1/diarize` | Speaker-Diarization via pyannote.audio |
| Ollama | HTTP/REST | `POST /v1/chat/completions` | OpenAI-kompatible LLM-API für Strukturierung und Zusammenfassung. Request: `{"model": "mistral", "messages": [...]}`. Response: `{"choices": [{"message": {"content": "..."}}]}`. |
| HuggingFace Hub | HTTPS | — | Einmaliger Modell-Download für pyannote (nur bei Erststart) |

### Ollama-Schnittstelle (Detail)

`stt-server` kommuniziert mit Ollama ausschließlich über einen einzigen Endpunkt:

```
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "mistral",
  "messages": [
    {"role": "system", "content": "<system-prompt>"},
    {"role": "user",   "content": "<transkript-text>"}
  ]
}
```

Antwort:
```json
{
  "choices": [
    {"message": {"content": "<strukturierter-text oder zusammenfassung>"}}
  ]
}
```

Ollama ist eine **externe Fremd-API**, die `stt-server` als HTTP-Client konsumiert.
Die Schnittstelle ist OpenAI-kompatibel — ein Wechsel zu einem anderen
OpenAI-kompatiblen LLM-Backend (z. B. LM Studio, vLLM) erfordert keine
Code-Änderungen, nur eine Anpassung von `LLM_BASE_URL` und `LLM_MODEL`.
