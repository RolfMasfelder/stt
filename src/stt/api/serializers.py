"""DRF serializers for request/response validation and OpenAPI documentation."""

from rest_framework import serializers

from .models import ResultVersion, StorageConfig

# --- Input serializers ---


class AudioUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Audio file (.wav, .mp3, .flac, .ogg, .m4a, .wma, .webm)",
    )
    model = serializers.CharField(
        default="small",
        help_text="Whisper model name",
    )


class ProcessUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        help_text="Audio file (.wav, .mp3, .flac, .ogg, .m4a, .wma, .webm)",
    )
    model = serializers.CharField(
        default="small",
        help_text="Whisper model name",
    )
    diarize = serializers.BooleanField(
        default=True,
        help_text="Enable speaker diarization",
    )


# --- Output serializers ---


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    llm = serializers.CharField(required=False)


class TranscribeResponseSerializer(serializers.Serializer):
    text = serializers.CharField()


class DiarizedSegmentSerializer(serializers.Serializer):
    speaker = serializers.CharField()
    start = serializers.FloatField()
    end = serializers.FloatField()
    text = serializers.CharField()


class DiarizeResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    diarized_text = serializers.CharField()
    segments = DiarizedSegmentSerializer(many=True)


class ProcessResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    diarized_text = serializers.CharField(allow_null=True)
    structured_text = serializers.CharField(allow_null=True)
    summary = serializers.CharField(allow_null=True)


class ErrorResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


# --- Job serializers (async task queue) ---


class JobResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    job_type = serializers.CharField()
    status = serializers.CharField()
    original_filename = serializers.CharField()
    whisper_model = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class JobDetailSerializer(JobResponseSerializer):
    result_text = serializers.CharField()
    result_diarized_text = serializers.CharField()
    result_structured_text = serializers.CharField()
    result_summary = serializers.CharField()
    result_segments_json = serializers.JSONField(allow_null=True)
    error_message = serializers.CharField()
    results_delivered = serializers.BooleanField()
    results_delivered_at = serializers.DateTimeField(allow_null=True)


# --- Storage config serializers (ADR-11, ADR-12) ---


class StorageConfigSerializer(serializers.ModelSerializer):
    """Serializer for StorageConfig CRUD operations.

    s3_secret_key is write-only — never returned in API responses.
    """

    class Meta:
        model = StorageConfig
        fields = [
            "id",
            "name",
            "backend_type",
            "is_default",
            "base_path",
            "s3_endpoint_url",
            "s3_bucket",
            "s3_access_key",
            "s3_secret_key",
            "s3_region",
            "encrypt_at_rest",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "s3_secret_key": {"write_only": True},
        }


# --- Correction workflow serializers (2d) ---


class JobUpdateSerializer(serializers.Serializer):
    """Input for correcting job result fields."""

    result_text = serializers.CharField(required=False, allow_blank=True)
    result_diarized_text = serializers.CharField(required=False, allow_blank=True)
    result_structured_text = serializers.CharField(required=False, allow_blank=True)
    result_summary = serializers.CharField(required=False, allow_blank=True)


class ReprocessSerializer(serializers.Serializer):
    """Input for selecting which steps to re-run."""

    steps = serializers.ListField(
        child=serializers.ChoiceField(choices=["structure", "summarize"]),
        min_length=1,
        help_text="Pipeline steps to re-run on current result text",
    )


class ResultVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResultVersion
        fields = [
            "id",
            "version",
            "result_text",
            "result_diarized_text",
            "result_structured_text",
            "result_summary",
            "source",
            "created_at",
        ]
        read_only_fields = fields


class StorageTestResponseSerializer(serializers.Serializer):
    """Response for the storage backend test endpoint."""

    status = serializers.ChoiceField(choices=["success", "error"])
    checks = serializers.DictField(child=serializers.BooleanField())
    message = serializers.CharField()
    duration_ms = serializers.IntegerField()


# --- GDPR serializers (2e) ---


class DeleteResponseSerializer(serializers.Serializer):
    """Response for deletion operations (DSGVO Art. 17)."""

    deleted_jobs = serializers.IntegerField()
    deleted_versions = serializers.IntegerField()
    deleted_audit_logs = serializers.IntegerField()


class DataExportJobSerializer(serializers.Serializer):
    """Job data included in GDPR data export."""

    id = serializers.UUIDField()
    job_type = serializers.CharField()
    status = serializers.CharField()
    whisper_model = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    result_text = serializers.CharField()
    result_diarized_text = serializers.CharField()
    result_structured_text = serializers.CharField()
    result_summary = serializers.CharField()


class DataExportVersionSerializer(serializers.Serializer):
    """Version data included in GDPR data export."""

    job_id = serializers.UUIDField(source="job.id")
    version = serializers.IntegerField()
    source = serializers.CharField()
    created_at = serializers.DateTimeField()
    result_text = serializers.CharField()
    result_diarized_text = serializers.CharField()
    result_structured_text = serializers.CharField()
    result_summary = serializers.CharField()


class DataExportSerializer(serializers.Serializer):
    """Full GDPR data export response (Art. 20)."""

    user = serializers.CharField()
    exported_at = serializers.DateTimeField()
    jobs = DataExportJobSerializer(many=True)
    versions = DataExportVersionSerializer(many=True)
    audit_logs = serializers.ListField(child=serializers.DictField())
