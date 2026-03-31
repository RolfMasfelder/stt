"""DRF views for STT API endpoints."""

import logging
import os
import tempfile
from dataclasses import replace
from pathlib import Path

from django.core.exceptions import ValidationError
from django_q.tasks import async_task
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from stt.config import AppConfig, WhisperConfig, load_config
from stt.diarize import DiarizationError, diarize_audio, format_diarized_segments
from stt.logging_setup import setup_logging
from stt.summarize import (
    SummarizationError,
    process_transcript,
    structure_text,
    summarize_text,
)
from stt.transcribe import TranscriptionError, transcribe_audio

from .audit import log_audit
from .models import (
    AuditAction,
    AuditLog,
    Job,
    JobType,
    ResultVersion,
    StorageConfig,
    Tenant,
)
from .serializers import (
    AudioUploadSerializer,
    DataExportJobSerializer,
    DataExportSerializer,
    DataExportVersionSerializer,
    DeleteResponseSerializer,
    DiarizeResponseSerializer,
    ErrorResponseSerializer,
    HealthResponseSerializer,
    JobDetailSerializer,
    JobResponseSerializer,
    JobUpdateSerializer,
    ProcessResponseSerializer,
    ProcessUploadSerializer,
    ReprocessSerializer,
    ResultVersionSerializer,
    StorageConfigSerializer,
    StorageTestResponseSerializer,
    TranscribeResponseSerializer,
)
from .throttles import UploadRateThrottle

logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
_ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".wma",
    ".webm",
}

_config: AppConfig | None = None


def _get_config() -> AppConfig:
    """Return the lazily-loaded ML configuration."""
    global _config  # noqa: PLW0603
    if _config is None:
        _config = load_config()
        setup_logging(_config.log_level)
        logger.info("STT Server started (config loaded)")
    return _config


def _save_upload(file: object) -> Path:
    """Validate and save an uploaded file to a temporary location."""
    suffix = Path(file.name).suffix.lower() if file.name else ".wav"
    if suffix not in _ALLOWED_AUDIO_EXTENSIONS:
        raise _AudioUploadError(
            f"Unsupported audio format: {suffix}",
            status.HTTP_400_BAD_REQUEST,
        )

    if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
        raise _AudioUploadError(
            f"File too large (max {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    fd, tmp_name = tempfile.mkstemp(suffix=suffix)
    try:
        for chunk in file.chunks():
            os.write(fd, chunk)
    finally:
        os.close(fd)
    return Path(tmp_name)


def _get_whisper_config(model: str) -> WhisperConfig:
    """Create a WhisperConfig with the given model name."""
    cfg = _get_config()
    return replace(cfg.whisper, model_name=model)


class _AudioUploadError(Exception):
    """Internal error for upload validation failures."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        responses={200: HealthResponseSerializer},
        summary="Health check",
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class TranscribeView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadRateThrottle]

    @extend_schema(
        request=AudioUploadSerializer,
        responses={
            200: TranscribeResponseSerializer,
            400: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        summary="Transcribe audio file",
    )
    def post(self, request: Request) -> Response:
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        model = request.data.get("model", "small")

        try:
            audio_path = _save_upload(file)
        except _AudioUploadError as e:
            return Response({"detail": e.detail}, status=e.status_code)

        try:
            whisper_cfg = _get_whisper_config(model)
            text = transcribe_audio(audio_path, whisper_cfg)
            return Response({"text": text})
        except TranscriptionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except FileNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            audio_path.unlink(missing_ok=True)


class DiarizeView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadRateThrottle]

    @extend_schema(
        request=AudioUploadSerializer,
        responses={
            200: DiarizeResponseSerializer,
            400: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
        },
        summary="Transcribe with speaker diarization",
    )
    def post(self, request: Request) -> Response:
        cfg = _get_config()
        if not cfg.diarize.hf_token:
            return Response(
                {"detail": "HF_STT_TOKEN not configured on server"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        model = request.data.get("model", "small")

        try:
            audio_path = _save_upload(file)
        except _AudioUploadError as e:
            return Response({"detail": e.detail}, status=e.status_code)

        try:
            whisper_cfg = _get_whisper_config(model)
            segments = diarize_audio(audio_path, whisper_cfg, cfg.diarize)
            diarized_text = format_diarized_segments(segments)
            plain_text = " ".join(seg.text for seg in segments)
            return Response(
                {
                    "text": plain_text,
                    "diarized_text": diarized_text,
                    "segments": [
                        {
                            "speaker": s.speaker,
                            "start": s.start,
                            "end": s.end,
                            "text": s.text,
                        }
                        for s in segments
                    ],
                },
            )
        except DiarizationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except FileNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            audio_path.unlink(missing_ok=True)


class ProcessView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadRateThrottle]

    @extend_schema(
        request=ProcessUploadSerializer,
        responses={
            200: ProcessResponseSerializer,
            400: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        summary="Full pipeline: transcribe, diarize, summarize",
    )
    def post(self, request: Request) -> Response:
        cfg = _get_config()

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        model = request.data.get("model", "small")
        do_diarize = str(request.data.get("diarize", "true")).lower() in (
            "true",
            "1",
            "yes",
        )

        try:
            audio_path = _save_upload(file)
        except _AudioUploadError as e:
            return Response({"detail": e.detail}, status=e.status_code)

        try:
            whisper_cfg = _get_whisper_config(model)

            diarized_text: str | None = None

            if do_diarize and cfg.diarize.hf_token:
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

            return Response(
                {
                    "text": plain_text,
                    "diarized_text": result.diarized_text,
                    "structured_text": result.structured_text,
                    "summary": result.summary,
                },
            )
        except (TranscriptionError, DiarizationError, SummarizationError) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except FileNotFoundError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            audio_path.unlink(missing_ok=True)


# --- Async Job endpoints ---

_JOB_TYPE_TASK_MAP = {
    JobType.TRANSCRIBE: "stt.api.tasks.run_transcribe",
    JobType.DIARIZE: "stt.api.tasks.run_diarize",
    JobType.PROCESS: "stt.api.tasks.run_process",
}


class JobCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadRateThrottle]

    @extend_schema(
        request=ProcessUploadSerializer,
        responses={
            202: JobResponseSerializer,
            400: ErrorResponseSerializer,
            413: ErrorResponseSerializer,
        },
        summary="Create async processing job",
        description=(
            "Upload an audio file and create an async job. "
            "Poll GET /v1/jobs/{id} for status and results."
        ),
    )
    def post(self, request: Request) -> Response:
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"detail": "No file provided"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Determine job type from query param (default: process).
        raw_type = request.data.get("job_type", JobType.PROCESS)
        if raw_type not in JobType.values:
            return Response(
                {"detail": f"Invalid job_type: {raw_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = request.data.get("model", "small")
        do_diarize = str(request.data.get("diarize", "true")).lower() in (
            "true",
            "1",
            "yes",
        )

        try:
            audio_path = _save_upload(file)
        except _AudioUploadError as e:
            return Response({"detail": e.detail}, status=e.status_code)

        job = Job.objects.create(
            job_type=raw_type,
            original_filename=str(audio_path),
            whisper_model=model,
            enable_diarize=do_diarize,
            owner=request.user if request.user.is_authenticated else None,
            tenant=getattr(request, "tenant", None),
        )

        log_audit(
            AuditAction.JOB_CREATED,
            request=request,
            resource_type="job",
            resource_id=str(job.id),
        )

        task_func = _JOB_TYPE_TASK_MAP[raw_type]
        async_task(task_func, str(job.id))

        return Response(
            JobResponseSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )


class JobDetailView(APIView):
    @extend_schema(
        responses={
            200: JobDetailSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Get job status and results",
    )
    def get(self, request: Request, job_id: str) -> Response:
        try:
            qs = Job.objects.all()
            tenant = getattr(request, "tenant", None)
            if tenant:
                qs = qs.filter(tenant=tenant)
            job = qs.get(id=job_id)
        except (Job.DoesNotExist, ValueError, ValidationError):
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(JobDetailSerializer(job).data)


# --- Correction workflow endpoints (2d) ---


def _get_job_or_404(job_id: str, tenant: Tenant | None = None) -> Job | None:
    """Return a Job or None if not found.  Filters by tenant if given."""
    try:
        qs = Job.objects.all()
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs.get(id=job_id)
    except (Job.DoesNotExist, ValueError, ValidationError):
        return None


def _create_version_snapshot(job: Job, source: str) -> ResultVersion:
    """Create a new ResultVersion from the current state of a Job."""
    last_version = (
        job.versions.order_by("-version").values_list("version", flat=True).first()
    )
    next_version = (last_version + 1) if last_version is not None else 0
    return ResultVersion.objects.create(
        job=job,
        version=next_version,
        result_text=job.result_text,
        result_diarized_text=job.result_diarized_text,
        result_structured_text=job.result_structured_text,
        result_summary=job.result_summary,
        source=source,
    )


class JobUpdateView(APIView):
    """Correct job result fields (creates a new version)."""

    @extend_schema(
        request=JobUpdateSerializer,
        responses={
            200: JobDetailSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Correct job results",
        description="Update result fields and create a versioned snapshot.",
    )
    def patch(self, request: Request, job_id: str) -> Response:
        job = _get_job_or_404(job_id, getattr(request, "tenant", None))
        if job is None:
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = JobUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_fields: list[str] = []
        for field in (
            "result_text",
            "result_diarized_text",
            "result_structured_text",
            "result_summary",
        ):
            if field in serializer.validated_data:
                setattr(job, field, serializer.validated_data[field])
                updated_fields.append(field)

        if not updated_fields:
            return Response(
                {"detail": "No fields to update"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_fields.append("updated_at")
        job.save(update_fields=updated_fields)

        _create_version_snapshot(job, source="correction")

        log_audit(
            AuditAction.JOB_UPDATED,
            request=request,
            resource_type="job",
            resource_id=str(job.id),
            detail=f"fields={','.join(f for f in updated_fields if f != 'updated_at')}",
        )

        return Response(JobDetailSerializer(job).data)


class JobReprocessView(APIView):
    """Re-run pipeline steps on existing job results."""

    @extend_schema(
        request=ReprocessSerializer,
        responses={
            200: JobDetailSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            500: ErrorResponseSerializer,
        },
        summary="Re-run pipeline steps",
        description=(
            "Re-run structure and/or summarize on the current result text. "
            "Creates a versioned snapshot of the new results."
        ),
    )
    def post(self, request: Request, job_id: str) -> Response:
        job = _get_job_or_404(job_id, getattr(request, "tenant", None))
        if job is None:
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReprocessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        steps = serializer.validated_data["steps"]
        source_text = job.result_text
        if not source_text:
            return Response(
                {"detail": "Job has no result text to reprocess"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cfg = _get_config()
        updated_fields: list[str] = []

        try:
            if "structure" in steps:
                job.result_structured_text = structure_text(source_text, cfg.lm_studio)
                updated_fields.append("result_structured_text")

            if "summarize" in steps:
                text_to_summarize = job.result_structured_text or source_text
                job.result_summary = summarize_text(text_to_summarize, cfg.lm_studio)
                updated_fields.append("result_summary")
        except SummarizationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        updated_fields.append("updated_at")
        job.save(update_fields=updated_fields)

        _create_version_snapshot(job, source="reprocess")

        log_audit(
            AuditAction.JOB_REPROCESSED,
            request=request,
            resource_type="job",
            resource_id=str(job.id),
            detail=f"steps={','.join(steps)}",
        )

        return Response(JobDetailSerializer(job).data)


class JobVersionListView(APIView):
    """List all versioned snapshots of a job's results."""

    @extend_schema(
        responses={
            200: ResultVersionSerializer(many=True),
            404: ErrorResponseSerializer,
        },
        summary="List result versions",
    )
    def get(self, request: Request, job_id: str) -> Response:
        job = _get_job_or_404(job_id, getattr(request, "tenant", None))
        if job is None:
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        versions = job.versions.all()
        return Response(ResultVersionSerializer(versions, many=True).data)


# --- Storage config endpoints (ADR-11, ADR-12) ---


class StorageConfigListView(APIView):
    """List and create storage backend configurations."""

    @extend_schema(
        responses={200: StorageConfigSerializer(many=True)},
        summary="List all storage configurations",
    )
    def get(self, request: Request) -> Response:
        qs = StorageConfig.objects.all()
        tenant = getattr(request, "tenant", None)
        if tenant:
            qs = qs.filter(tenant=tenant)
        return Response(StorageConfigSerializer(qs, many=True).data)

    @extend_schema(
        request=StorageConfigSerializer,
        responses={
            201: StorageConfigSerializer,
            400: ErrorResponseSerializer,
        },
        summary="Create a storage configuration",
    )
    def post(self, request: Request) -> Response:
        serializer = StorageConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        config = serializer.save(tenant=getattr(request, "tenant", None))
        log_audit(
            AuditAction.STORAGE_CONFIG_CREATED,
            request=request,
            resource_type="storage_config",
            resource_id=str(config.id),
        )
        return Response(
            StorageConfigSerializer(config).data,
            status=status.HTTP_201_CREATED,
        )


class StorageConfigDetailView(APIView):
    """Retrieve, update, and delete a storage backend configuration."""

    @staticmethod
    def _get_config(config_id: str, tenant: Tenant | None) -> StorageConfig | None:
        try:
            qs = StorageConfig.objects.all()
            if tenant:
                qs = qs.filter(tenant=tenant)
            return qs.get(id=config_id)
        except (StorageConfig.DoesNotExist, ValueError, ValidationError):
            return None

    @extend_schema(
        responses={
            200: StorageConfigSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Get a storage configuration",
    )
    def get(self, request: Request, config_id: str) -> Response:
        config = self._get_config(config_id, getattr(request, "tenant", None))
        if config is None:
            return Response(
                {"detail": "Storage config not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(StorageConfigSerializer(config).data)

    @extend_schema(
        request=StorageConfigSerializer,
        responses={
            200: StorageConfigSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Update a storage configuration",
    )
    def put(self, request: Request, config_id: str) -> Response:
        config = self._get_config(config_id, getattr(request, "tenant", None))
        if config is None:
            return Response(
                {"detail": "Storage config not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = StorageConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        config = serializer.save()
        log_audit(
            AuditAction.STORAGE_CONFIG_UPDATED,
            request=request,
            resource_type="storage_config",
            resource_id=str(config.id),
        )
        return Response(StorageConfigSerializer(config).data)

    @extend_schema(
        responses={
            204: None,
            404: ErrorResponseSerializer,
        },
        summary="Delete a storage configuration",
    )
    def delete(self, request: Request, config_id: str) -> Response:
        config = self._get_config(config_id, getattr(request, "tenant", None))
        if config is None:
            return Response(
                {"detail": "Storage config not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        config_id_str = str(config.id)
        config.delete()
        log_audit(
            AuditAction.STORAGE_CONFIG_DELETED,
            request=request,
            resource_type="storage_config",
            resource_id=config_id_str,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class StorageConfigTestView(APIView):
    """Test a storage backend configuration (ADR-12)."""

    @extend_schema(
        request=None,
        responses={
            200: StorageTestResponseSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Test storage backend connectivity",
    )
    def post(self, request: Request, config_id: str) -> Response:
        from .storage import StorageError, get_backend

        tenant = getattr(request, "tenant", None)
        try:
            qs = StorageConfig.objects.all()
            if tenant:
                qs = qs.filter(tenant=tenant)
            config = qs.get(id=config_id)
        except (StorageConfig.DoesNotExist, ValueError, ValidationError):
            return Response(
                {"detail": "Storage config not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            backend = get_backend(config)
        except StorageError as e:
            return Response(
                {
                    "status": "error",
                    "checks": {
                        "connection": False,
                        "write": False,
                        "read": False,
                        "delete": False,
                    },
                    "message": str(e),
                    "duration_ms": 0,
                },
            )

        result = backend.test_connection()
        log_audit(
            AuditAction.STORAGE_CONFIG_TESTED,
            request=request,
            resource_type="storage_config",
            resource_id=str(config.id),
            detail=f"success={result.success}",
        )
        return Response(
            {
                "status": "success" if result.success else "error",
                "checks": {
                    "connection": result.connection,
                    "write": result.write,
                    "read": result.read,
                    "delete": result.delete,
                },
                "message": result.message,
                "duration_ms": result.duration_ms,
            },
        )


# --- GDPR endpoints (2e) ---


class JobDeleteView(APIView):
    """Delete a single job and all associated data (DSGVO Art. 17)."""

    @extend_schema(
        responses={
            200: DeleteResponseSerializer,
            403: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Delete a job (DSGVO Art. 17)",
        description="Permanently deletes a job, its versions, and related audit logs.",
    )
    def delete(self, request: Request, job_id: str) -> Response:
        tenant = getattr(request, "tenant", None)
        try:
            qs = Job.objects.all()
            if tenant:
                qs = qs.filter(tenant=tenant)
            job = qs.get(id=job_id)
        except (Job.DoesNotExist, ValueError, ValidationError):
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only the owner (or staff) may delete.
        if job.owner != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Not allowed to delete this job"},
                status=status.HTTP_403_FORBIDDEN,
            )

        job_id_str = str(job.id)
        deleted_versions = job.versions.count()
        job.versions.all().delete()

        deleted_audit = AuditLog.objects.filter(
            resource_type="job",
            resource_id=job_id_str,
        ).count()
        AuditLog.objects.filter(
            resource_type="job",
            resource_id=job_id_str,
        ).delete()

        job.delete()

        log_audit(
            AuditAction.DATA_DELETED,
            request=request,
            resource_type="job",
            resource_id=job_id_str,
            detail=f"versions={deleted_versions},audit_logs={deleted_audit}",
        )

        return Response(
            {
                "deleted_jobs": 1,
                "deleted_versions": deleted_versions,
                "deleted_audit_logs": deleted_audit,
            },
        )


class UserDataDeleteView(APIView):
    """Delete ALL data for the authenticated user (DSGVO Art. 17)."""

    @extend_schema(
        responses={
            200: DeleteResponseSerializer,
            400: ErrorResponseSerializer,
        },
        summary="Delete all user data (DSGVO Art. 17)",
        description=(
            "Permanently deletes all jobs, versions, and audit logs "
            "belonging to the authenticated user."
        ),
    )
    def delete(self, request: Request) -> Response:
        user = request.user
        actor = user.username or str(user.pk)
        tenant = getattr(request, "tenant", None)

        jobs = Job.objects.filter(owner=user)
        if tenant:
            jobs = jobs.filter(tenant=tenant)
        job_ids = list(jobs.values_list("id", flat=True))
        job_id_strs = [str(jid) for jid in job_ids]

        deleted_versions = ResultVersion.objects.filter(job_id__in=job_ids).count()
        ResultVersion.objects.filter(job_id__in=job_ids).delete()

        deleted_audit = AuditLog.objects.filter(
            resource_type="job",
            resource_id__in=job_id_strs,
        ).count()
        # Also delete user-level audit logs (by actor name).
        deleted_audit += (
            AuditLog.objects.filter(actor=actor)
            .exclude(
                resource_type="job",
                resource_id__in=job_id_strs,
            )
            .count()
        )
        AuditLog.objects.filter(
            resource_type="job",
            resource_id__in=job_id_strs,
        ).delete()
        AuditLog.objects.filter(actor=actor).delete()

        deleted_jobs = jobs.count()
        jobs.delete()

        # Log the deletion itself (this entry is the only trace left).
        log_audit(
            AuditAction.USER_DATA_DELETED,
            request=request,
            resource_type="user",
            resource_id=actor,
            detail=f"jobs={deleted_jobs},versions={deleted_versions},audit_logs={deleted_audit}",
        )

        return Response(
            {
                "deleted_jobs": deleted_jobs,
                "deleted_versions": deleted_versions,
                "deleted_audit_logs": deleted_audit,
            },
        )


class UserDataExportView(APIView):
    """Export all user data as JSON (DSGVO Art. 20 — Datenportabilität)."""

    @extend_schema(
        responses={
            200: DataExportSerializer,
        },
        summary="Export all user data (DSGVO Art. 20)",
        description=(
            "Returns all jobs, result versions, and audit log entries "
            "belonging to the authenticated user in a portable JSON format."
        ),
    )
    def get(self, request: Request) -> Response:
        from django.utils import timezone

        user = request.user
        actor = user.username or str(user.pk)
        tenant = getattr(request, "tenant", None)

        jobs = Job.objects.filter(owner=user)
        if tenant:
            jobs = jobs.filter(tenant=tenant)
        job_ids = list(jobs.values_list("id", flat=True))
        job_id_strs = [str(jid) for jid in job_ids]

        versions = ResultVersion.objects.filter(job_id__in=job_ids)

        audit_logs = AuditLog.objects.filter(
            resource_type="job",
            resource_id__in=job_id_strs,
        ) | AuditLog.objects.filter(actor=actor)
        audit_data = list(
            audit_logs.order_by("created_at").values(
                "action",
                "resource_type",
                "resource_id",
                "detail",
                "created_at",
            )
        )

        log_audit(
            AuditAction.DATA_EXPORTED,
            request=request,
            resource_type="user",
            resource_id=actor,
            detail=f"jobs={jobs.count()},versions={versions.count()}",
        )

        return Response(
            {
                "user": actor,
                "exported_at": timezone.now(),
                "jobs": DataExportJobSerializer(jobs, many=True).data,
                "versions": DataExportVersionSerializer(versions, many=True).data,
                "audit_logs": audit_data,
            },
        )
