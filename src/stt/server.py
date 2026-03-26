"""FastAPI server for STT processing (transcription, diarization, summarization)."""

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile
from pydantic import BaseModel

from stt.config import load_config
from stt.diarize import DiarizationError, diarize_audio, format_diarized_segments
from stt.logging_setup import setup_logging
from stt.summarize import SummarizationError, process_transcript
from stt.transcribe import TranscriptionError, transcribe_audio

config = load_config()
setup_logging(config.log_level)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="STT Server API",
    description="Speech-to-Text Server mit Transkription, Sprechererkennung und Zusammenfassung",
    version="1.0.0",
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


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/v1/transcribe")
async def transcribe(
    file: UploadFile, model: str = Form("small")
) -> TranscribeResponse:
    audio_path = await _save_upload(file)
    try:
        from dataclasses import replace

        whisper_cfg = replace(config.whisper, model_name=model)
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
        from dataclasses import replace

        whisper_cfg = replace(config.whisper, model_name=model)
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
        from dataclasses import replace

        whisper_cfg = replace(config.whisper, model_name=model)

        diarized_text: str | None = None

        if diarize and config.diarize.hf_token:
            segments = diarize_audio(audio_path, whisper_cfg, config.diarize)
            diarized_text = format_diarized_segments(segments)
            plain_text = " ".join(seg.text for seg in segments)
        else:
            plain_text = transcribe_audio(audio_path, whisper_cfg)

        structured, summary, diarized = process_transcript(
            plain_text,
            config.lm_studio,
            diarize=False,
            diarized_text=diarized_text,
        )

        return ProcessResponse(
            text=plain_text,
            diarized_text=diarized,
            structured_text=structured,
            summary=summary,
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
