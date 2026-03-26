"""FastAPI server for STT processing (transcription, diarization, summarization)."""

import logging
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

config: AppConfig = None  # type: ignore[assignment]


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
    suffix = Path(upload.filename).suffix if upload.filename else ".wav"
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix, dir=tempfile.gettempdir()
    )
    try:
        content = await upload.read()
        tmp.write(content)
        tmp.flush()
        return Path(tmp.name)
    finally:
        tmp.close()


def _get_whisper_config(model: str) -> WhisperConfig:
    """Create a WhisperConfig with the given model name."""
    return replace(config.whisper, model_name=model)


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
    except (TranscriptionError, FileNotFoundError) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)


@app.post("/v1/diarize")
async def diarize(file: UploadFile, model: str = Form("small")) -> DiarizeResponse:
    if not config.diarize.hf_token:
        raise HTTPException(
            status_code=500, detail="HF_STT_TOKEN not configured on server"
        )

    audio_path = await _save_upload(file)
    try:
        whisper_cfg = _get_whisper_config(model)
        segments = diarize_audio(audio_path, whisper_cfg, config.diarize)
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
    except (DiarizationError, FileNotFoundError) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)


@app.post("/v1/process")
async def process(
    file: UploadFile, model: str = Form("small"), diarize: bool = Form(True)
) -> ProcessResponse:
    audio_path = await _save_upload(file)
    try:
        whisper_cfg = _get_whisper_config(model)

        diarized_text: str | None = None

        if diarize and config.diarize.hf_token:
            segments = diarize_audio(audio_path, whisper_cfg, config.diarize)
            diarized_text = format_diarized_segments(segments)
            plain_text = " ".join(seg.text for seg in segments)
        else:
            plain_text = transcribe_audio(audio_path, whisper_cfg)

        result = process_transcript(
            plain_text,
            config.lm_studio,
            diarize=False,
            diarized_text=diarized_text,
        )

        return ProcessResponse(
            text=plain_text,
            diarized_text=result.diarized_text,
            structured_text=result.structured_text,
            summary=result.summary,
        )
    except (
        TranscriptionError,
        DiarizationError,
        SummarizationError,
        FileNotFoundError,
    ) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        audio_path.unlink(missing_ok=True)
