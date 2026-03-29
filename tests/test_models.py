"""Tests for the STT API Django models."""

import pytest

from stt.api.models import (
    AuditAction,
    AuditLog,
    Job,
    JobStatus,
    JobType,
    StorageBackendType,
    StorageConfig,
)


@pytest.mark.django_db
class TestJobModel:
    """Tests for the Job model."""

    def test_create_job_defaults(self) -> None:
        job = Job.objects.create(job_type=JobType.TRANSCRIBE)
        assert job.id is not None
        assert job.status == JobStatus.PENDING
        assert job.job_type == JobType.TRANSCRIBE
        assert job.whisper_model == "small"
        assert job.enable_diarize is True
        assert job.result_text == ""
        assert job.error_message == ""

    def test_create_job_all_types(self) -> None:
        for jt in JobType:
            job = Job.objects.create(job_type=jt)
            assert job.job_type == jt

    def test_job_status_transitions(self) -> None:
        job = Job.objects.create(job_type=JobType.PROCESS)
        assert job.status == JobStatus.PENDING

        job.status = JobStatus.RUNNING
        job.save()
        job.refresh_from_db()
        assert job.status == JobStatus.RUNNING

        job.status = JobStatus.COMPLETED
        job.result_text = "Hello World"
        job.save()
        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Hello World"

    def test_job_failed_with_error(self) -> None:
        job = Job.objects.create(
            job_type=JobType.DIARIZE,
            status=JobStatus.FAILED,
            error_message="HF token not configured",
        )
        job.refresh_from_db()
        assert job.status == JobStatus.FAILED
        assert "HF token" in job.error_message

    def test_job_str(self) -> None:
        job = Job.objects.create(job_type=JobType.TRANSCRIBE)
        s = str(job)
        assert "transcribe" in s
        assert "pending" in s

    def test_job_ordering(self) -> None:
        Job.objects.create(job_type=JobType.TRANSCRIBE)
        j2 = Job.objects.create(job_type=JobType.DIARIZE)
        jobs = list(Job.objects.all())
        assert jobs[0].id == j2.id  # newest first

    def test_job_segments_json(self) -> None:
        segments = [
            {"speaker": "Sprecher 1", "start": 0.0, "end": 1.5, "text": "Hallo"},
        ]
        job = Job.objects.create(
            job_type=JobType.DIARIZE,
            result_segments_json=segments,
        )
        job.refresh_from_db()
        assert job.result_segments_json == segments


@pytest.mark.django_db
class TestStorageConfigModel:
    """Tests for the StorageConfig model."""

    def test_create_local_storage(self) -> None:
        cfg = StorageConfig.objects.create(
            name="Lokaler Speicher",
            backend_type=StorageBackendType.LOCAL,
            base_path="/data/output",
        )
        assert cfg.id is not None
        assert cfg.backend_type == StorageBackendType.LOCAL
        assert cfg.base_path == "/data/output"

    def test_create_s3_storage(self) -> None:
        cfg = StorageConfig.objects.create(
            name="EU S3",
            backend_type=StorageBackendType.S3,
            s3_endpoint_url="https://s3.eu-central-1.ionoscloud.com",
            s3_bucket="stt-results",
            s3_access_key="AKTEST",
            s3_secret_key="secret123",
            s3_region="de",
        )
        cfg.refresh_from_db()
        assert cfg.backend_type == StorageBackendType.S3
        assert cfg.s3_bucket == "stt-results"

    def test_is_default(self) -> None:
        cfg = StorageConfig.objects.create(
            name="Default",
            backend_type=StorageBackendType.LOCAL,
            is_default=True,
        )
        assert cfg.is_default is True

    def test_str(self) -> None:
        cfg = StorageConfig.objects.create(
            name="Test",
            backend_type=StorageBackendType.S3,
        )
        assert "Test" in str(cfg)
        assert "s3" in str(cfg)

    def test_ordering(self) -> None:
        StorageConfig.objects.create(
            name="Bravo", backend_type=StorageBackendType.LOCAL
        )
        StorageConfig.objects.create(
            name="Alpha", backend_type=StorageBackendType.LOCAL
        )
        configs = list(StorageConfig.objects.all())
        assert configs[0].name == "Alpha"


@pytest.mark.django_db
class TestAuditLogModel:
    """Tests for the AuditLog model."""

    def test_create_audit_entry(self) -> None:
        log = AuditLog.objects.create(
            action=AuditAction.JOB_CREATED,
            resource_type="job",
            resource_id="some-uuid",
            actor="testuser",
            ip_address="192.168.1.1",
        )
        assert log.id is not None
        assert log.action == AuditAction.JOB_CREATED
        assert log.actor == "testuser"

    def test_all_actions_valid(self) -> None:
        for action in AuditAction:
            log = AuditLog.objects.create(action=action)
            assert log.action == action

    def test_audit_ordering(self) -> None:
        AuditLog.objects.create(action=AuditAction.JOB_CREATED)
        l2 = AuditLog.objects.create(action=AuditAction.JOB_COMPLETED)
        logs = list(AuditLog.objects.all())
        assert logs[0].id == l2.id  # newest first

    def test_str(self) -> None:
        log = AuditLog.objects.create(
            action=AuditAction.RESULT_DELETED,
            resource_type="job",
            resource_id="abc-123",
        )
        s = str(log)
        assert "result_deleted" in s
        assert "job" in s

    def test_ip_address_nullable(self) -> None:
        log = AuditLog.objects.create(action=AuditAction.JOB_CREATED)
        assert log.ip_address is None
