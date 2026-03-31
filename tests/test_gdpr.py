"""Tests for GDPR endpoints (Phase 2e): Lösch-API, Auto-Delete, Datenexport."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application
from rest_framework.test import APIClient

from stt.api.models import AuditAction, AuditLog, Job, JobStatus, JobType, ResultVersion

# --- Fixtures ---


@pytest.fixture
def other_user(db):
    """Create a second user for ownership tests."""
    User = get_user_model()
    return User.objects.create_user(username="otheruser", password="otherpass123")


@pytest.fixture
def other_auth_client(other_user, db):
    """Authenticated client for the other user."""
    app = Application.objects.create(
        name="other-app",
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        user=other_user,
    )
    token = AccessToken.objects.create(
        user=other_user,
        token="other-access-token-99999",
        application=app,
        expires=timezone.now() + timedelta(hours=1),
        scope="read write",
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.token}")
    return client


@pytest.fixture
def job_with_owner(test_user, db):
    """Create a completed job owned by test_user."""
    job = Job.objects.create(
        job_type=JobType.TRANSCRIBE,
        status=JobStatus.COMPLETED,
        owner=test_user,
        result_text="Test transcription",
        result_summary="Test summary",
    )
    ResultVersion.objects.create(
        job=job,
        version=0,
        result_text="Test transcription",
        source="pipeline",
    )
    AuditLog.objects.create(
        action=AuditAction.JOB_CREATED,
        resource_type="job",
        resource_id=str(job.id),
        actor=test_user.username,
    )
    AuditLog.objects.create(
        action=AuditAction.JOB_COMPLETED,
        resource_type="job",
        resource_id=str(job.id),
        actor=test_user.username,
    )
    return job


@pytest.fixture
def job_with_other_owner(other_user, db):
    """Create a job owned by a different user."""
    return Job.objects.create(
        job_type=JobType.TRANSCRIBE,
        status=JobStatus.COMPLETED,
        owner=other_user,
        result_text="Other user text",
    )


# --- 2e.1: Lösch-API (Art. 17) ---


class TestJobDelete:
    """DELETE /v1/jobs/<id>/delete — single job deletion."""

    def test_delete_own_job(self, auth_client, job_with_owner):
        """Owner can delete their own job."""
        job_id = str(job_with_owner.id)
        url = reverse("job-delete", kwargs={"job_id": job_id})
        response = auth_client.delete(url)

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_jobs"] == 1
        assert data["deleted_versions"] >= 1
        assert data["deleted_audit_logs"] >= 2

        # Job is gone.
        assert not Job.objects.filter(id=job_id).exists()
        assert not ResultVersion.objects.filter(job_id=job_id).exists()

    def test_delete_other_users_job_forbidden(
        self,
        auth_client,
        job_with_other_owner,
    ):
        """Cannot delete another user's job."""
        url = reverse("job-delete", kwargs={"job_id": str(job_with_other_owner.id)})
        response = auth_client.delete(url)

        assert response.status_code == 403
        assert Job.objects.filter(id=job_with_other_owner.id).exists()

    def test_delete_nonexistent_job_404(self, auth_client):
        """Deleting a non-existent job returns 404."""
        url = reverse(
            "job-delete",
            kwargs={"job_id": "00000000-0000-0000-0000-000000000000"},
        )
        response = auth_client.delete(url)
        assert response.status_code == 404

    def test_delete_creates_audit_log(self, auth_client, job_with_owner):
        """Deletion creates a DATA_DELETED audit entry."""
        job_id = str(job_with_owner.id)
        url = reverse("job-delete", kwargs={"job_id": job_id})
        auth_client.delete(url)

        entry = AuditLog.objects.filter(action=AuditAction.DATA_DELETED).first()
        assert entry is not None
        assert entry.resource_id == job_id


class TestUserDataDelete:
    """DELETE /v1/user/data — delete all user data."""

    def test_delete_all_user_data(self, auth_client, job_with_owner, test_user):
        """Deletes all jobs, versions, and audit logs for the user."""
        # Create a second job for the same user.
        _job2 = Job.objects.create(
            job_type=JobType.PROCESS,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Second job",
        )

        url = reverse("user-data-delete")
        response = auth_client.delete(url)

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_jobs"] == 2

        # All jobs gone.
        assert Job.objects.filter(owner=test_user).count() == 0

    def test_delete_preserves_other_users_data(
        self,
        auth_client,
        job_with_owner,
        job_with_other_owner,
        other_user,
    ):
        """Deleting user data does not affect other users."""
        url = reverse("user-data-delete")
        auth_client.delete(url)

        assert Job.objects.filter(owner=other_user).count() == 1

    def test_delete_creates_user_data_deleted_audit(
        self,
        auth_client,
        job_with_owner,
        test_user,
    ):
        """Creates a USER_DATA_DELETED audit entry."""
        url = reverse("user-data-delete")
        auth_client.delete(url)

        entry = AuditLog.objects.filter(
            action=AuditAction.USER_DATA_DELETED,
        ).first()
        assert entry is not None
        assert entry.resource_id == test_user.username


# --- 2e.2: Auto-Delete ---


class TestAutoDelete:
    """auto_delete_expired_jobs task."""

    def test_deletes_expired_jobs(self, test_user, db, settings):
        """Jobs older than retention period are deleted."""
        settings.DATA_RETENTION_DAYS = 30

        # Create an old completed job (40 days ago).
        old_job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Old text",
        )
        Job.objects.filter(id=old_job.id).update(
            created_at=timezone.now() - timedelta(days=40),
        )
        ResultVersion.objects.create(
            job=old_job,
            version=0,
            result_text="Old text",
            source="pipeline",
        )

        # Create a recent job (should survive).
        recent_job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Recent text",
        )

        from stt.api.tasks import auto_delete_expired_jobs

        deleted = auto_delete_expired_jobs()

        assert deleted == 1
        assert not Job.objects.filter(id=old_job.id).exists()
        assert Job.objects.filter(id=recent_job.id).exists()

    def test_disabled_when_zero(self, db, settings):
        """No deletion when DATA_RETENTION_DAYS=0."""
        settings.DATA_RETENTION_DAYS = 0

        from stt.api.tasks import auto_delete_expired_jobs

        deleted = auto_delete_expired_jobs()
        assert deleted == 0

    def test_skips_pending_and_running_jobs(self, test_user, db, settings):
        """Only completed/failed jobs are auto-deleted."""
        settings.DATA_RETENTION_DAYS = 30

        pending_job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.PENDING,
            owner=test_user,
        )
        Job.objects.filter(id=pending_job.id).update(
            created_at=timezone.now() - timedelta(days=40),
        )

        running_job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.RUNNING,
            owner=test_user,
        )
        Job.objects.filter(id=running_job.id).update(
            created_at=timezone.now() - timedelta(days=40),
        )

        from stt.api.tasks import auto_delete_expired_jobs

        deleted = auto_delete_expired_jobs()
        assert deleted == 0
        assert Job.objects.filter(id=pending_job.id).exists()
        assert Job.objects.filter(id=running_job.id).exists()

    def test_creates_audit_log(self, test_user, db, settings):
        """Auto-delete creates a DATA_AUTO_DELETED audit entry."""
        settings.DATA_RETENTION_DAYS = 30

        old_job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
        )
        Job.objects.filter(id=old_job.id).update(
            created_at=timezone.now() - timedelta(days=40),
        )

        from stt.api.tasks import auto_delete_expired_jobs

        auto_delete_expired_jobs()

        entry = AuditLog.objects.filter(
            action=AuditAction.DATA_AUTO_DELETED,
        ).first()
        assert entry is not None
        assert entry.actor == "system"


# --- 2e.3: Datenexport (Art. 20) ---


class TestUserDataExport:
    """GET /v1/user/data/export — GDPR data portability."""

    def test_export_user_data(self, auth_client, job_with_owner, test_user):
        """Returns all user data as JSON."""
        url = reverse("user-data-export")
        response = auth_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["user"] == test_user.username
        assert "exported_at" in data
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["id"] == str(job_with_owner.id)
        assert data["jobs"][0]["result_text"] == "Test transcription"
        assert len(data["versions"]) >= 1
        assert len(data["audit_logs"]) >= 2

    def test_export_excludes_other_users(
        self,
        auth_client,
        job_with_owner,
        job_with_other_owner,
    ):
        """Export only contains the authenticated user's data."""
        url = reverse("user-data-export")
        response = auth_client.get(url)

        data = response.json()
        job_ids = [j["id"] for j in data["jobs"]]
        assert str(job_with_owner.id) in job_ids
        assert str(job_with_other_owner.id) not in job_ids

    def test_export_creates_audit_log(self, auth_client, job_with_owner, test_user):
        """Export creates a DATA_EXPORTED audit entry."""
        url = reverse("user-data-export")
        auth_client.get(url)

        entry = AuditLog.objects.filter(action=AuditAction.DATA_EXPORTED).first()
        assert entry is not None
        assert entry.resource_id == test_user.username

    def test_export_empty_user(self, auth_client, test_user):
        """Export works for a user with no data."""
        url = reverse("user-data-export")
        response = auth_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["versions"] == []
