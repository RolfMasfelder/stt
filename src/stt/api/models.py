"""Django models for the STT API."""

import uuid

from django.conf import settings
from django.db import models


class Tenant(models.Model):
    """SaaS tenant for multi-tenancy with RLS (FA-25).

    Each tenant represents a customer organisation.
    All data-bearing models reference a tenant via ForeignKey.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(
        max_length=100, unique=True, help_text="URL-safe identifier"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


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

    # Owner — set from request.user on creation (DSGVO Art. 17/20).
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )

    # Multi-tenancy (FA-25): isolates data per customer organisation.
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="jobs",
        db_index=True,
    )

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

    # Encryption at rest (ADR-08)
    encrypt_at_rest = models.BooleanField(
        default=False,
        help_text="Encrypt stored files with AES-256-GCM before writing",
    )

    # Multi-tenancy (FA-25)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="storage_configs",
        db_index=True,
    )

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
    JOB_UPDATED = "job_updated", "Job Updated"
    JOB_REPROCESSED = "job_reprocessed", "Job Reprocessed"
    RESULT_ACCESSED = "result_accessed", "Result Accessed"
    RESULT_DELETED = "result_deleted", "Result Deleted"
    DATA_DELETED = "data_deleted", "Data Deleted"
    DATA_AUTO_DELETED = "data_auto_deleted", "Data Auto-Deleted"
    DATA_EXPORTED = "data_exported", "Data Exported"
    USER_DATA_DELETED = "user_data_deleted", "User Data Deleted"
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

    # Multi-tenancy (FA-25)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.created_at}] {self.action} on {self.resource_type}/{self.resource_id}"


class ResultVersion(models.Model):
    """Versioned snapshot of job results for correction workflow (FA-18).

    Created automatically when a job completes (version 0)
    and on each correction/reprocessing step.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField(default=0)

    result_text = models.TextField(blank=True, default="")
    result_diarized_text = models.TextField(blank=True, default="")
    result_structured_text = models.TextField(blank=True, default="")
    result_summary = models.TextField(blank=True, default="")

    source = models.CharField(
        max_length=30,
        default="pipeline",
        help_text="How this version was created: pipeline, correction, reprocess",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["version"]
        unique_together = [("job", "version")]

    def __str__(self) -> str:
        return f"Job {self.job_id} v{self.version} ({self.source})"
