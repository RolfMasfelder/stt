"""FastAPI server for STT processing (transcription, diarization, summarization)."""

import logging
import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from pydantic import BaseModel

from stt.config import AppConfig, WhisperConfig, load_config
from stt.diarize import DiarizationError, diarize_audio, format_diarized_segments
from stt.logging_setup import setup_logging
from stt.summarize import SummarizationError, process_transcript
from stt.transcribe import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB
_ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".wma",
    ".webm",
}

config: AppConfig | None = None


def _ensure_config() -> AppConfig:
    """Return the loaded config or raise if server is not initialized."""
    if config is None:
        raise RuntimeError("Server not initialized — lifespan not triggered")
    return config


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Load configuration on startup."""
    global config  # noqa: PLW0603
    config = load_config()
    setup_logging(config.log_level)
    logger.info("STT Server started")
    yield


app = FastAPI(
    title="STT Server API",
    description="Speech-to-Text Server mit Transkription, Sprechererkennung und Zusammenfassung",
    version="1.0.0",
    lifespan=lifespan,
)


class HealthResponse(BaseModel):
    status: str


class TranscribeResponse(BaseModel):
    text: str


class DiarizedSegmentModel(BaseModel):
    speaker: str
    start: float
    end: float
    text: str


class DiarizeResponse(BaseModel):
    text: str
    diarized_text: str
    segments: list[DiarizedSegmentModel]


class ProcessResponse(BaseModel):
    text: str
    diarized_text: str | None
    structured_text: str
    summary: str


async def _save_upload(upload: UploadFile) -> Path:
    """Save an uploaded file to a temporary location and return the path."""
    suffix = Path(upload.filename).suffix.lower() if upload.filename else ".wav"
    if suffix not in _ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {suffix}",
        )

    content = await upload.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )

    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    return Path(tmp_name)


def _get_whisper_config(model: str) -> WhisperConfig:
    """Create a WhisperConfig with the given model name."""
    cfg = _ensure_config()
    return replace(cfg.whisper, model_name=model)


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/transcribe")
async def transcribe(
    file: UploadFile, model: str = Form("small")
) -> TranscribeResponse:
    audio_path = await _save_upload(file)
    try:
        whisper_cfg = _get_whisper_config(model)
        text = transcribe_audio(audio_path, whisper_cfg)
        return TranscribeResponse(text=text)
    except TranscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)


@app.post("/v1/diarize")
async def diarize(file: UploadFile, model: str = Form("small")) -> DiarizeResponse:
    cfg = _ensure_config()
    if not cfg.diarize.hf_token:
        raise HTTPException(
            status_code=503, detail="HF_STT_TOKEN not configured on server"
        )

    audio_path = await _save_upload(file)
    try:
        whisper_cfg = _get_whisper_config(model)
        segments = diarize_audio(audio_path, whisper_cfg, cfg.diarize)
        diarized_text = format_diarized_segments(segments)
        plain_text = " ".join(seg.text for seg in segments)
        return DiarizeResponse(
            text=plain_text,
            diarized_text=diarized_text,
            segments=[
                DiarizedSegmentModel(
                    speaker=s.speaker, start=s.start, end=s.end, text=s.text
                )
                for s in segments
            ],
        )
    except DiarizationError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)


@app.post("/v1/process")
async def process(
    file: UploadFile, model: str = Form("small"), diarize: bool = Form(True)
) -> ProcessResponse:
    cfg = _ensure_config()
    audio_path = await _save_upload(file)
    try:
        whisper_cfg = _get_whisper_config(model)

        diarized_text: str | None = None

        if diarize and cfg.diarize.hf_token:
            segments = diarize_audio(audio_path, whisper_cfg, cfg.diarize)
            diarized_text = format_diarized_segments(segments)
            plain_text = " ".join(seg.text for seg in segments)
        else:
            plain_text = transcribe_audio(audio_path, whisper_cfg)

        result = process_transcript(
            plain_text,
            cfg.lm_studio,
            diarize=False,
            diarized_text=diarized_text,
        )

        return ProcessResponse(
            text=plain_text,
            diarized_text=result.diarized_text,
            structured_text=result.structured_text,
            summary=result.summary,
        )
    except (TranscriptionError, DiarizationError, SummarizationError) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)
