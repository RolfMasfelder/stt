"""Django models for the STT API."""

import uuid

from django.db import models


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class JobType(models.TextChoices):
    TRANSCRIBE = "transcribe", "Transcribe"
    DIARIZE = "diarize", "Diarize"
    PROCESS = "process", "Process"


class Job(models.Model):
    """Asynchronous processing job (FA-19).

    Audio uploads create a Job that is processed via django-q2.
    Clients poll the status and retrieve results when completed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=20, choices=JobType.choices)
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )

    # Input metadata (no raw audio stored — only the temp path while processing).
    original_filename = models.CharField(max_length=512, blank=True, default="")
    whisper_model = models.CharField(max_length=50, default="small")
    enable_diarize = models.BooleanField(default=True)

    # Results (stored as text/JSON once processing completes).
    result_text = models.TextField(blank=True, default="")
    result_diarized_text = models.TextField(blank=True, default="")
    result_structured_text = models.TextField(blank=True, default="")
    result_summary = models.TextField(blank=True, default="")
    result_segments_json = models.JSONField(blank=True, null=True)

    # Error details for failed jobs.
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Job {self.id} [{self.job_type}/{self.status}]"


class StorageBackendType(models.TextChoices):
    LOCAL = "local", "Local Filesystem"
    S3 = "s3", "S3-compatible"


class StorageConfig(models.Model):
    """Configurable storage backend for results (FA-13, FA-14, ADR-11, ADR-12).

    Users configure where processed results are stored (local FS, S3, etc.).
    The default behaviour (direct response) requires no StorageConfig.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Display name for this backend")
    backend_type = models.CharField(max_length=20, choices=StorageBackendType.choices)
    is_default = models.BooleanField(
        default=False,
        help_text="Use as default storage for new jobs",
    )

    # Common settings
    base_path = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text="Base path / prefix for stored files",
    )

    # S3-specific settings (encrypted at rest in a future step — ADR-08).
    s3_endpoint_url = models.URLField(blank=True, default="")
    s3_bucket = models.CharField(max_length=255, blank=True, default="")
    s3_access_key = models.CharField(max_length=255, blank=True, default="")
    s3_secret_key = models.CharField(max_length=255, blank=True, default="")
    s3_region = models.CharField(max_length=100, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.backend_type})"


class AuditAction(models.TextChoices):
    JOB_CREATED = "job_created", "Job Created"
    JOB_COMPLETED = "job_completed", "Job Completed"
    JOB_FAILED = "job_failed", "Job Failed"
    RESULT_ACCESSED = "result_accessed", "Result Accessed"
    RESULT_DELETED = "result_deleted", "Result Deleted"
    STORAGE_CONFIG_CREATED = "storage_config_created", "Storage Config Created"
    STORAGE_CONFIG_UPDATED = "storage_config_updated", "Storage Config Updated"
    STORAGE_CONFIG_DELETED = "storage_config_deleted", "Storage Config Deleted"
    STORAGE_CONFIG_TESTED = "storage_config_tested", "Storage Config Tested"
    AUTH_FAILED = "auth_failed", "Authentication Failed"
    RATE_LIMITED = "rate_limited", "Rate Limited"


class AuditLog(models.Model):
    """Immutable audit trail for DSGVO Art. 30 compliance (FA-16).

    Records who did what and when. Never stores audio or text content.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=30, choices=AuditAction.choices, db_index=True)

    # Resource reference (generic: job ID, storage config ID, etc.).
    resource_type = models.CharField(max_length=50, blank=True, default="")
    resource_id = models.CharField(max_length=50, blank=True, default="")

    # Actor — will be populated from auth once OAuth2 is active (2a.6).
    actor = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Username or client-id of the actor",
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    detail = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Short machine-readable detail (no content data)",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.action} on {self.resource_type}/{self.resource_id}"
