"""ML Service: FastAPI microservice for transcription and speaker diarization.

Provides two endpoints:
  POST /v1/transcribe  – audio → plain text
  POST /v1/diarize     – audio → speaker-labeled segments
"""

import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import torch
import torchaudio
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from pyannote.core import Annotation

logger = logging.getLogger(__name__)

app = FastAPI(title="STT ML Service", version="0.1.0")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
DIARIZE_MODEL: str = os.getenv("DIARIZE_MODEL", "pyannote/speaker-diarization-3.1")
DIARIZE_DEVICE: str = os.getenv("DIARIZE_DEVICE", "cpu")
HF_STT_TOKEN: str | None = os.getenv("HF_STT_TOKEN") or None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DiarizedSegment:
    """A text segment with speaker label and timestamps."""

    speaker: str
    start: float
    end: float
    text: str


# ---------------------------------------------------------------------------
# Whisper helpers
# ---------------------------------------------------------------------------
def _run_whisper(
    audio_path: Path, model_name: str, language: str | None = None
) -> list[dict]:
    """Run faster-whisper locally, return segments as dicts."""
    model = WhisperModel(
        model_name, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE
    )
    lang = None if language in (None, "auto") else language
    segments, info = model.transcribe(str(audio_path), language=lang)
    logger.info(
        "Detected language: %s (probability: %.2f)",
        info.language,
        info.language_probability,
    )
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]


def _transcribe_text(
    audio_path: Path, model_name: str, language: str | None = None
) -> str:
    """Transcribe audio to plain text."""
    segments = _run_whisper(audio_path, model_name, language)
    return " ".join(s["text"] for s in segments).strip()


# ---------------------------------------------------------------------------
# Diarization helpers
# ---------------------------------------------------------------------------
def _run_diarization(audio_path: Path) -> Annotation:
    """Run pyannote speaker diarization on audio."""
    if not HF_STT_TOKEN:
        raise ValueError("HF_STT_TOKEN not configured on ML service")

    pipeline = Pipeline.from_pretrained(DIARIZE_MODEL, token=HF_STT_TOKEN)

    if DIARIZE_DEVICE != "cpu":
        pipeline.to(torch.device(DIARIZE_DEVICE))

    waveform, sample_rate = torchaudio.load(str(audio_path))
    result = pipeline({"waveform": waveform, "sample_rate": sample_rate})

    if hasattr(result, "speaker_diarization"):
        return result.speaker_diarization
    return result


def _assign_speaker(start: float, end: float, diarization: Annotation) -> str:
    """Find the speaker that covers most of a given time range."""
    speakers: dict[str, float] = {}
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        overlap_start = max(start, turn.start)
        overlap_end = min(end, turn.end)
        if overlap_start < overlap_end:
            speakers[speaker] = speakers.get(speaker, 0.0) + (
                overlap_end - overlap_start
            )
    if speakers:
        return max(speakers, key=speakers.get)
    return "UNKNOWN"


def _diarize(
    audio_path: Path, model_name: str, language: str | None = None
) -> list[dict]:
    """Transcribe + diarize, returning segment dicts with speaker labels."""
    # Step 1: whisper segments with timestamps
    whisper_segments = _run_whisper(audio_path, model_name, language)

    # Step 2: pyannote diarization
    diarization = _run_diarization(audio_path)

    # Step 3: assign speakers
    result: list[DiarizedSegment] = []
    for seg in whisper_segments:
        if seg["text"]:
            speaker = _assign_speaker(seg["start"], seg["end"], diarization)
            result.append(
                DiarizedSegment(
                    speaker=speaker,
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"],
                )
            )

    # Normalize speaker names (SPEAKER_00 → Sprecher 1)
    speaker_map: dict[str, str] = {}
    normalized = []
    for seg in result:
        if seg.speaker not in speaker_map:
            speaker_map[seg.speaker] = f"Sprecher {len(speaker_map) + 1}"
        normalized.append(
            {
                "speaker": speaker_map[seg.speaker],
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
            }
        )

    return normalized


# ---------------------------------------------------------------------------
# Helper: save upload to temp file
# ---------------------------------------------------------------------------
def _save_upload(upload: UploadFile) -> Path:
    """Save an uploaded file to a temporary location."""
    suffix = Path(upload.filename or "audio.wav").suffix or ".wav"
    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    try:
        data = upload.file.read()
        os.write(fd, data)
    finally:
        os.close(fd)
    return Path(tmp_name)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/transcribe")
def transcribe(
    file: UploadFile = File(...),
    model: str = Form(WHISPER_MODEL),
    language: str = Form("auto"),
) -> dict:
    """Transcribe audio file to plain text."""
    audio_path = _save_upload(file)
    try:
        text = _transcribe_text(audio_path, model, language)
        return {"text": text}
    except Exception as e:
        logger.exception("Transcription failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)


@app.post("/v1/diarize")
def diarize(
    file: UploadFile = File(...),
    model: str = Form(WHISPER_MODEL),
    language: str = Form("auto"),
) -> dict:
    """Transcribe with speaker diarization."""
    if not HF_STT_TOKEN:
        raise HTTPException(status_code=503, detail="HF_STT_TOKEN not configured")

    audio_path = _save_upload(file)
    try:
        segments = _diarize(audio_path, model, language)
        plain_text = " ".join(s["text"] for s in segments)
        # Build formatted diarized text
        diarized_text = _format_segments(segments)
        return {
            "text": plain_text,
            "diarized_text": diarized_text,
            "segments": segments,
        }
    except Exception as e:
        logger.exception("Diarization failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)


def _format_segments(segments: list[dict]) -> str:
    """Format diarized segments as readable text with speaker labels."""
    if not segments:
        return ""

    lines: list[str] = []
    current_speaker: str | None = None
    current_texts: list[str] = []

    for seg in segments:
        if seg["speaker"] != current_speaker:
            if current_speaker is not None:
                lines.append(f"**{current_speaker}:**\n{' '.join(current_texts)}")
            current_speaker = seg["speaker"]
            current_texts = [seg["text"]]
        else:
            current_texts.append(seg["text"])

    if current_speaker is not None:
        lines.append(f"**{current_speaker}:**\n{' '.join(current_texts)}")

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    uvicorn.run(app, host="0.0.0.0", port=8091)
