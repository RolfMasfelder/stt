"""Tests for persistent audio storage (2f.8), delivery tracking (2f.9),
and audio cleanup after delivery (2f.10)."""

import uuid
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from django.utils import timezone

from stt.api.models import AuditAction, AuditLog, Job, JobStatus, JobType
from stt.api.tasks import cleanup_delivered_audio, run_transcribe
from stt.config import WhisperConfig


@pytest.fixture
def client(auth_client):
    """Authenticated client with mocked ML config."""
    mock_config = MagicMock()
    mock_config.log_level = "WARNING"
    mock_config.whisper = WhisperConfig()

    with patch("stt.api.views._get_config", return_value=mock_config):
        yield auth_client


def _audio_file(name: str = "test.wav", content: bytes = b"fake audio data"):
    f = BytesIO(content)
    f.name = name
    return f


# --- 2f.8: Persistent audio storage ---


@pytest.mark.django_db
class TestAudioPersistentStorage:
    """POST /v1/jobs stores audio in storage backend."""

    @patch("stt.api.views.async_task")
    @patch("stt.api.storage.get_audio_backend")
    def test_audio_stored_in_backend(
        self, mock_get_backend, mock_async, client
    ) -> None:
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(), "job_type": "transcribe"},
            format="multipart",
        )
        assert response.status_code == 202
        job_id = response.json()["id"]

        job = Job.objects.get(id=job_id)
        assert job.audio_storage_path != ""
        assert job.audio_storage_path.endswith(".wav")
        assert str(job.id) in job.audio_storage_path

        mock_backend.store.assert_called_once()
        call_args = mock_backend.store.call_args
        assert call_args[0][1] == job.audio_storage_path  # filename arg

    @patch("stt.api.views.async_task")
    @patch("stt.api.storage.get_audio_backend")
    def test_audio_preserves_extension(
        self, mock_get_backend, mock_async, client
    ) -> None:
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(name="recording.mp3"), "job_type": "transcribe"},
            format="multipart",
        )
        assert response.status_code == 202
        job = Job.objects.get(id=response.json()["id"])
        assert job.audio_storage_path.endswith(".mp3")

    @patch("stt.api.views.async_task")
    @patch("stt.api.storage.get_audio_backend")
    def test_storage_failure_falls_back_to_temp(
        self, mock_get_backend, mock_async, client
    ) -> None:
        mock_backend = MagicMock()
        mock_backend.store.side_effect = RuntimeError("S3 unavailable")
        mock_get_backend.return_value = mock_backend

        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(), "job_type": "transcribe"},
            format="multipart",
        )
        assert response.status_code == 202
        job = Job.objects.get(id=response.json()["id"])
        # Fallback: original_filename is a temp path, audio_storage_path is empty.
        assert job.audio_storage_path == ""
        assert job.original_filename != ""

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.transcribe_audio")
    @patch("stt.api.storage.get_audio_backend")
    def test_task_retrieves_from_storage_backend(
        self, mock_get_backend, mock_transcribe, mock_config
    ) -> None:
        mock_config.return_value = MagicMock(whisper=WhisperConfig())
        mock_transcribe.return_value = "Hello World"

        mock_backend = MagicMock()
        mock_backend.retrieve.return_value = b"fake audio data"
        mock_get_backend.return_value = mock_backend

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            audio_storage_path=f"{uuid.uuid4()}.wav",
            original_filename="upload.wav",
        )

        run_transcribe(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Hello World"
        mock_backend.retrieve.assert_called_once_with(job.audio_storage_path)

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.storage.get_audio_backend")
    def test_task_fails_if_audio_not_in_storage(
        self, mock_get_backend, mock_config
    ) -> None:
        mock_config.return_value = MagicMock(whisper=WhisperConfig())
        mock_backend = MagicMock()
        mock_backend.retrieve.side_effect = RuntimeError("Not found")
        mock_get_backend.return_value = mock_backend

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            audio_storage_path=f"{uuid.uuid4()}.wav",
        )

        run_transcribe(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.FAILED
        assert "Failed to retrieve audio" in job.error_message

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.transcribe_audio")
    def test_task_legacy_temp_path_still_works(
        self, mock_transcribe, mock_config
    ) -> None:
        """Jobs without audio_storage_path fall back to original_filename."""
        mock_config.return_value = MagicMock(whisper=WhisperConfig())
        mock_transcribe.return_value = "Legacy text"

        tmp = Path("/tmp/test_legacy_audio.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            original_filename=str(tmp),
            audio_storage_path="",
        )

        run_transcribe(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Legacy text"


# --- 2f.9: Results delivery tracking ---


@pytest.mark.django_db
class TestResultsDeliveryTracking:
    """GET /v1/jobs/{id} sets results_delivered on completed jobs."""

    def test_completed_job_marks_delivered(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            result_text="Transcribed text",
        )
        assert job.results_delivered is False

        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["results_delivered"] is True
        assert data["results_delivered_at"] is not None

        job.refresh_from_db()
        assert job.results_delivered is True
        assert job.results_delivered_at is not None

    def test_pending_job_not_marked_delivered(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.PENDING,
        )

        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200

        job.refresh_from_db()
        assert job.results_delivered is False
        assert job.results_delivered_at is None

    def test_failed_job_not_marked_delivered(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.FAILED,
            error_message="Error",
        )

        client.get(f"/v1/jobs/{job.id}")

        job.refresh_from_db()
        assert job.results_delivered is False

    def test_second_access_does_not_change_timestamp(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            result_text="Text",
        )

        client.get(f"/v1/jobs/{job.id}")
        job.refresh_from_db()
        first_ts = job.results_delivered_at

        client.get(f"/v1/jobs/{job.id}")
        job.refresh_from_db()
        assert job.results_delivered_at == first_ts

    def test_delivery_creates_audit_log(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            result_text="Text",
        )

        client.get(f"/v1/jobs/{job.id}")

        entry = AuditLog.objects.filter(
            action=AuditAction.RESULT_ACCESSED,
            resource_id=str(job.id),
            detail="results_delivered=true",
        ).first()
        assert entry is not None


# --- 2f.10: Audio deletion after delivery / auto-delete ---


@pytest.mark.django_db
class TestAudioCleanupAfterDelivery:
    """cleanup_delivered_audio scheduled task."""

    @patch("stt.api.storage.get_audio_backend")
    def test_cleanup_deletes_delivered_audio(
        self, mock_get_backend, test_user, db, settings
    ) -> None:
        settings.AUDIO_CLEANUP_GRACE_HOURS = 1

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path=f"{uuid.uuid4()}.wav",
            results_delivered=True,
            results_delivered_at=timezone.now() - timedelta(hours=2),
        )

        cleaned = cleanup_delivered_audio()

        assert cleaned == 1
        mock_backend.delete.assert_called_once_with(job.audio_storage_path)

        job.refresh_from_db()
        assert job.audio_storage_path == ""

    @patch("stt.api.storage.get_audio_backend")
    def test_cleanup_respects_grace_period(
        self, mock_get_backend, test_user, db, settings
    ) -> None:
        settings.AUDIO_CLEANUP_GRACE_HOURS = 24

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path=f"{uuid.uuid4()}.wav",
            results_delivered=True,
            results_delivered_at=timezone.now() - timedelta(hours=1),  # Within grace.
        )

        cleaned = cleanup_delivered_audio()

        assert cleaned == 0
        mock_backend.delete.assert_not_called()

    @patch("stt.api.storage.get_audio_backend")
    def test_cleanup_skips_undelivered_jobs(
        self, mock_get_backend, test_user, db, settings
    ) -> None:
        settings.AUDIO_CLEANUP_GRACE_HOURS = 1

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path=f"{uuid.uuid4()}.wav",
            results_delivered=False,
        )

        cleaned = cleanup_delivered_audio()

        assert cleaned == 0
        mock_backend.delete.assert_not_called()

    @patch("stt.api.storage.get_audio_backend")
    def test_cleanup_skips_already_cleaned_jobs(
        self, mock_get_backend, test_user, db, settings
    ) -> None:
        settings.AUDIO_CLEANUP_GRACE_HOURS = 1

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path="",  # Already cleaned.
            results_delivered=True,
            results_delivered_at=timezone.now() - timedelta(hours=2),
        )

        cleaned = cleanup_delivered_audio()

        assert cleaned == 0

    @patch("stt.api.storage.get_audio_backend")
    def test_cleanup_creates_audit_log(
        self, mock_get_backend, test_user, db, settings
    ) -> None:
        settings.AUDIO_CLEANUP_GRACE_HOURS = 1

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        audio_path = f"{uuid.uuid4()}.wav"
        Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path=audio_path,
            results_delivered=True,
            results_delivered_at=timezone.now() - timedelta(hours=2),
        )

        cleanup_delivered_audio()

        entry = AuditLog.objects.filter(
            action=AuditAction.AUDIO_DELETED,
            actor="system",
        ).first()
        assert entry is not None
        assert audio_path in entry.detail


@pytest.mark.django_db
class TestJobDeleteCleansAudio:
    """DELETE /v1/jobs/{id}/delete also removes audio from storage."""

    @patch("stt.api.storage.get_audio_backend")
    def test_delete_job_deletes_audio(
        self, mock_get_backend, auth_client, test_user
    ) -> None:
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        audio_path = f"{uuid.uuid4()}.wav"
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path=audio_path,
        )

        url = reverse("job-delete", kwargs={"job_id": str(job.id)})
        response = auth_client.delete(url)

        assert response.status_code == 200
        mock_backend.delete.assert_called_once_with(audio_path)

    def test_delete_job_without_audio_works(self, auth_client, test_user) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Text",
            audio_storage_path="",
        )

        url = reverse("job-delete", kwargs={"job_id": str(job.id)})
        response = auth_client.delete(url)

        assert response.status_code == 200
        assert not Job.objects.filter(id=job.id).exists()


@pytest.mark.django_db
class TestUserDataDeleteCleansAudio:
    """DELETE /v1/user/data also removes audio from storage."""

    @patch("stt.api.storage.get_audio_backend")
    def test_user_data_delete_cleans_audio(
        self, mock_get_backend, auth_client, test_user
    ) -> None:
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        paths = []
        for _ in range(2):
            p = f"{uuid.uuid4()}.wav"
            paths.append(p)
            Job.objects.create(
                job_type=JobType.TRANSCRIBE,
                status=JobStatus.COMPLETED,
                owner=test_user,
                result_text="Text",
                audio_storage_path=p,
            )

        url = reverse("user-data-delete")
        response = auth_client.delete(url)

        assert response.status_code == 200
        assert mock_backend.delete.call_count == 2
        deleted_paths = [call[0][0] for call in mock_backend.delete.call_args_list]
        for p in paths:
            assert p in deleted_paths


@pytest.mark.django_db
class TestAutoDeleteCleansAudio:
    """auto_delete_expired_jobs also removes audio from storage."""

    @patch("stt.api.storage.get_audio_backend")
    def test_auto_delete_cleans_audio(
        self, mock_get_backend, test_user, db, settings
    ) -> None:
        settings.DATA_RETENTION_DAYS = 30

        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        audio_path = f"{uuid.uuid4()}.wav"
        old_job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            owner=test_user,
            result_text="Old text",
            audio_storage_path=audio_path,
        )
        Job.objects.filter(id=old_job.id).update(
            created_at=timezone.now() - timedelta(days=40),
        )

        from stt.api.tasks import auto_delete_expired_jobs

        deleted = auto_delete_expired_jobs()

        assert deleted == 1
        mock_backend.delete.assert_called_once_with(audio_path)
