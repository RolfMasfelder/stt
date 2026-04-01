"""Async task functions dispatched via django-q2.

Each task receives a Job UUID, loads the Job from the database,
runs the ML pipeline, and writes back the results.
Also contains the GDPR auto-delete scheduled task (2e.2)
and audio cleanup after delivery (2f.10).
"""

import logging
import os
import tempfile
import time
import uuid
from pathlib import Path

from stt.config import AppConfig, WhisperConfig, load_config
from stt.diarize import diarize_audio, format_diarized_segments
from stt.summarize import process_transcript
from stt.transcribe import transcribe_audio

from .audit import log_audit
from .metrics import GDPR_DELETED, JOB_DURATION, JOBS_COMPLETED, JOBS_FAILED
from .models import AuditAction, AuditLog, Job, JobStatus, ResultVersion

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
    JOBS_FAILED.labels(job_type=job.job_type).inc()
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


def _retrieve_audio(job: Job) -> Path | None:
    """Retrieve audio for a job, returning a temp file path.

    Tries storage backend first (2f.8), falls back to legacy temp path.
    Returns None and fails the job if audio cannot be found.
    """
    if job.audio_storage_path:
        try:
            from .storage import get_audio_backend

            audio_backend = get_audio_backend()
            audio_data = audio_backend.retrieve(job.audio_storage_path)
            suffix = Path(job.audio_storage_path).suffix or ".wav"
            fd, tmp_name = tempfile.mkstemp(suffix=suffix)
            try:
                os.write(fd, audio_data)
            finally:
                os.close(fd)
            return Path(tmp_name)
        except Exception as exc:
            _fail_job(job, f"Failed to retrieve audio from storage: {exc}")
            return None

    # Legacy: direct temp file path.
    audio_path = Path(job.original_filename)
    if not audio_path.exists():
        _fail_job(job, f"Audio file not found: {audio_path}")
        return None
    return audio_path


def run_transcribe(job_id: str) -> None:
    """Transcribe audio for the given Job."""
    try:
        job = Job.objects.get(id=uuid.UUID(job_id))
    except Job.DoesNotExist:
        logger.error("Job %s not found", job_id)
        return

    audio_path = _retrieve_audio(job)
    if audio_path is None:
        return

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    _start = time.monotonic()
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
        JOBS_COMPLETED.labels(job_type=job.job_type).inc()
        JOB_DURATION.labels(job_type=job.job_type).observe(time.monotonic() - _start)
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

    audio_path = _retrieve_audio(job)
    if audio_path is None:
        return

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    _start = time.monotonic()
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
        JOBS_COMPLETED.labels(job_type=job.job_type).inc()
        JOB_DURATION.labels(job_type=job.job_type).observe(time.monotonic() - _start)
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

    audio_path = _retrieve_audio(job)
    if audio_path is None:
        return

    job.status = JobStatus.RUNNING
    job.save(update_fields=["status", "updated_at"])

    _start = time.monotonic()
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
        JOBS_COMPLETED.labels(job_type=job.job_type).inc()
        JOB_DURATION.labels(job_type=job.job_type).observe(time.monotonic() - _start)
        log_audit(
            AuditAction.JOB_COMPLETED,
            resource_type="job",
            resource_id=str(job.id),
        )
    except Exception as exc:
        _fail_job(job, str(exc))
    finally:
        audio_path.unlink(missing_ok=True)


# --- GDPR auto-delete (2e.2, ADR-13) ---


def auto_delete_expired_jobs() -> int:
    """Delete jobs older than DATA_RETENTION_DAYS.

    Designed to be called as a django-q2 scheduled task.
    Returns the number of deleted jobs.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    retention_days = getattr(settings, "DATA_RETENTION_DAYS", 0)
    if retention_days <= 0:
        logger.info("Auto-delete disabled (DATA_RETENTION_DAYS=%s)", retention_days)
        return 0

    cutoff = timezone.now() - timedelta(days=retention_days)
    expired_jobs = Job.objects.filter(
        created_at__lt=cutoff,
        status__in=[JobStatus.COMPLETED, JobStatus.FAILED],
    )

    total = expired_jobs.count()
    if total == 0:
        logger.info("Auto-delete: no expired jobs found (cutoff=%s)", cutoff)
        return 0

    # Delete associated versions and audit logs first.
    job_ids = list(expired_jobs.values_list("id", flat=True))
    job_id_strs = [str(jid) for jid in job_ids]

    # Delete audio from storage backend (2f.10).
    audio_paths = list(
        expired_jobs.exclude(audio_storage_path="").values_list(
            "audio_storage_path", flat=True
        )
    )
    if audio_paths:
        try:
            from .storage import get_audio_backend

            audio_backend = get_audio_backend()
            for path in audio_paths:
                try:
                    audio_backend.delete(path)
                except Exception:
                    logger.warning("Auto-delete: failed to delete audio %s", path)
        except Exception:
            logger.warning("Auto-delete: failed to init audio backend", exc_info=True)

    deleted_versions = ResultVersion.objects.filter(job_id__in=job_ids).delete()[0]
    deleted_audit = AuditLog.objects.filter(
        resource_type="job",
        resource_id__in=job_id_strs,
    ).delete()[0]

    expired_jobs.delete()

    GDPR_DELETED.inc(total)

    log_audit(
        AuditAction.DATA_AUTO_DELETED,
        resource_type="system",
        detail=f"jobs={total},versions={deleted_versions},audit_logs={deleted_audit},cutoff={cutoff.isoformat()}",
        actor="system",
    )

    logger.info(
        "Auto-delete: removed %d expired jobs (%d versions, %d audit logs)",
        total,
        deleted_versions,
        deleted_audit,
    )
    return total


# --- Audio cleanup after delivery (2f.10, FA-24) ---


def cleanup_delivered_audio() -> int:
    """Delete audio for jobs whose results have been delivered.

    Waits AUDIO_CLEANUP_GRACE_HOURS after delivery before deleting.
    Designed to be called as a django-q2 scheduled task.
    Returns the number of cleaned jobs.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    grace_hours = getattr(settings, "AUDIO_CLEANUP_GRACE_HOURS", 24)
    cutoff = timezone.now() - timedelta(hours=grace_hours)

    eligible = Job.objects.filter(
        results_delivered=True,
        results_delivered_at__lt=cutoff,
    ).exclude(audio_storage_path="")

    total = eligible.count()
    if total == 0:
        logger.info("Audio cleanup: no eligible jobs found")
        return 0

    try:
        from .storage import get_audio_backend

        audio_backend = get_audio_backend()
    except Exception:
        logger.error("Audio cleanup: failed to init audio backend", exc_info=True)
        return 0

    cleaned = 0
    for job in eligible.iterator():
        try:
            audio_backend.delete(job.audio_storage_path)
            old_path = job.audio_storage_path
            job.audio_storage_path = ""
            job.save(update_fields=["audio_storage_path", "updated_at"])
            cleaned += 1
            log_audit(
                AuditAction.AUDIO_DELETED,
                resource_type="job",
                resource_id=str(job.id),
                detail=f"path={old_path}",
                actor="system",
            )
        except Exception:
            logger.warning("Audio cleanup: failed for job %s", job.id, exc_info=True)

    logger.info("Audio cleanup: deleted audio for %d/%d jobs", cleaned, total)
    return cleaned
