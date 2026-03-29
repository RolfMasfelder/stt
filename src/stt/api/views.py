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
from stt.summarize import SummarizationError, process_transcript
from stt.transcribe import TranscriptionError, transcribe_audio

from .audit import log_audit
from .models import AuditAction, Job, JobType, StorageConfig
from .serializers import (
    AudioUploadSerializer,
    DiarizeResponseSerializer,
    ErrorResponseSerializer,
    HealthResponseSerializer,
    JobDetailSerializer,
    JobResponseSerializer,
    ProcessResponseSerializer,
    ProcessUploadSerializer,
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
            job = Job.objects.get(id=job_id)
        except (Job.DoesNotExist, ValueError, ValidationError):
            return Response(
                {"detail": "Job not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(JobDetailSerializer(job).data)


# --- Storage config endpoints (ADR-11, ADR-12) ---


class StorageConfigListView(APIView):
    """List and create storage backend configurations."""

    @extend_schema(
        responses={200: StorageConfigSerializer(many=True)},
        summary="List all storage configurations",
    )
    def get(self, request: Request) -> Response:
        configs = StorageConfig.objects.all()
        return Response(StorageConfigSerializer(configs, many=True).data)

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
        config = serializer.save()
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

    @extend_schema(
        responses={
            200: StorageConfigSerializer,
            404: ErrorResponseSerializer,
        },
        summary="Get a storage configuration",
    )
    def get(self, request: Request, config_id: str) -> Response:
        try:
            config = StorageConfig.objects.get(id=config_id)
        except (StorageConfig.DoesNotExist, ValueError, ValidationError):
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
        try:
            config = StorageConfig.objects.get(id=config_id)
        except (StorageConfig.DoesNotExist, ValueError, ValidationError):
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
        try:
            config = StorageConfig.objects.get(id=config_id)
        except (StorageConfig.DoesNotExist, ValueError, ValidationError):
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

        try:
            config = StorageConfig.objects.get(id=config_id)
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
