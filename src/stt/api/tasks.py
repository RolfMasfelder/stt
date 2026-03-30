"""Async task functions dispatched via django-q2.

Each task receives a Job UUID, loads the Job from the database,
runs the ML pipeline, and writes back the results.
"""

import logging
import uuid
from pathlib import Path

from stt.config import AppConfig, WhisperConfig, load_config
from stt.diarize import diarize_audio, format_diarized_segments
from stt.summarize import process_transcript
from stt.transcribe import transcribe_audio

from .audit import log_audit
from .models import AuditAction, Job, JobStatus, ResultVersion

logger = logging.getLogger(__name__)

_config: AppConfig | None = None


def _get_config() -> AppConfig:
    global _config  # noqa: PLW0603
    if _config is None:
        _config = load_config()
    return _config


def _get_whisper_config(model: str) -> WhisperConfig:
    from dataclasses import replace

    cfg = _get_config()
    return replace(cfg.whisper, model_name=model)


def _fail_job(job: Job, error: str) -> None:
    job.status = JobStatus.FAILED
    job.error_message = error
    job.save(update_fields=["status", "error_message", "updated_at"])
    log_audit(
        AuditAction.JOB_FAILED,
        resource_type="job",
        resource_id=str(job.id),
        detail=error[:500],
    )


def _create_initial_version(job: Job) -> None:
    """Create version 0 snapshot after pipeline completion."""
    ResultVersion.objects.create(
        job=job,
        version=0,
        result_text=job.result_text,
        result_diarized_text=job.result_diarized_text,
        result_structured_text=job.result_structured_text,
        result_summary=job.result_summary,
        source="pipeline",
    )


def run_transcribe(job_id: str) -> None:
    """Transcribe audio for the given Job."""
    try:
        job = Job.objects.get(id=uuid.UUID(job_id))
    except Job.DoesNotExist:
        logger.error("Job %s not found", job_id)
        return

    audio_path = Path(job.original_filename)
    if not audio_path.exists():
        _fail_job(job, f"Audio file not found: {audio_path}")
        return

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        whisper_cfg = _get_whisper_config(job.whisper_model)
        text = transcribe_audio(audio_path, whisper_cfg)
        job.status = JobStatus.COMPLETED
        job.result_text = text
        job.save(
            update_fields=[
                "status",
                "result_text",
                "updated_at",
            ]
        )
        _create_initial_version(job)
        log_audit(
            AuditAction.JOB_COMPLETED,
            resource_type="job",
            resource_id=str(job.id),
        )
    except Exception as exc:
        _fail_job(job, str(exc))
    finally:
        audio_path.unlink(missing_ok=True)


def run_diarize(job_id: str) -> None:
    """Transcribe with speaker diarization for the given Job."""
    try:
        job = Job.objects.get(id=uuid.UUID(job_id))
    except Job.DoesNotExist:
        logger.error("Job %s not found", job_id)
        return

    audio_path = Path(job.original_filename)
    if not audio_path.exists():
        _fail_job(job, f"Audio file not found: {audio_path}")
        return

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        cfg = _get_config()
        whisper_cfg = _get_whisper_config(job.whisper_model)
        segments = diarize_audio(audio_path, whisper_cfg, cfg.diarize)
        diarized_text = format_diarized_segments(segments)
        plain_text = " ".join(seg.text for seg in segments)

        job.status = JobStatus.COMPLETED
        job.result_text = plain_text
        job.result_diarized_text = diarized_text
        job.result_segments_json = [
            {
                "speaker": s.speaker,
                "start": s.start,
                "end": s.end,
                "text": s.text,
            }
            for s in segments
        ]
        job.save(
            update_fields=[
                "status",
                "result_text",
                "result_diarized_text",
                "result_segments_json",
                "updated_at",
            ]
        )
        _create_initial_version(job)
        log_audit(
            AuditAction.JOB_COMPLETED,
            resource_type="job",
            resource_id=str(job.id),
        )
    except Exception as exc:
        _fail_job(job, str(exc))
    finally:
        audio_path.unlink(missing_ok=True)


def run_process(job_id: str) -> None:
    """Full pipeline: transcribe, optionally diarize, then summarize."""
    try:
        job = Job.objects.get(id=uuid.UUID(job_id))
    except Job.DoesNotExist:
        logger.error("Job %s not found", job_id)
        return

    audio_path = Path(job.original_filename)
    if not audio_path.exists():
        _fail_job(job, f"Audio file not found: {audio_path}")
        return

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        cfg = _get_config()
        whisper_cfg = _get_whisper_config(job.whisper_model)

        diarized_text: str | None = None

        if job.enable_diarize and cfg.diarize.hf_token:
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

        job.status = JobStatus.COMPLETED
        job.result_text = plain_text
        job.result_diarized_text = result.diarized_text or ""
        job.result_structured_text = result.structured_text
        job.result_summary = result.summary
        job.save(
            update_fields=[
                "status",
                "result_text",
                "result_diarized_text",
                "result_structured_text",
                "result_summary",
                "updated_at",
            ]
        )
        _create_initial_version(job)
        log_audit(
            AuditAction.JOB_COMPLETED,
            resource_type="job",
            resource_id=str(job.id),
        )
    except Exception as exc:
        _fail_job(job, str(exc))
    finally:
        audio_path.unlink(missing_ok=True)
