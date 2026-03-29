"""Tests for django-q2 task queue integration and Job endpoints."""

import uuid
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.api.models import AuditAction, AuditLog, Job, JobStatus, JobType
from stt.api.tasks import run_diarize, run_process, run_transcribe
from stt.config import DiarizeConfig, LMStudioConfig, WhisperConfig
from stt.summarize import ProcessResult


@pytest.fixture
def client(auth_client):
    """Create an authenticated DRF test client with mocked ML config."""
    mock_config = MagicMock()
    mock_config.log_level = "WARNING"
    mock_config.whisper = WhisperConfig()
    mock_config.diarize = DiarizeConfig(hf_token="hf_test")
    mock_config.lm_studio = LMStudioConfig()

    with patch("stt.api.views._get_config", return_value=mock_config):
        yield auth_client


def _audio_file(name: str = "test.wav", content: bytes = b"fake audio data"):
    f = BytesIO(content)
    f.name = name
    return f


# === Job endpoint tests ===


@pytest.mark.django_db
class TestJobCreateEndpoint:
    """Tests for POST /v1/jobs."""

    @patch("stt.api.views.async_task")
    def test_create_job_returns_202(self, mock_async, client) -> None:
        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(), "job_type": "process"},
            format="multipart",
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["job_type"] == "process"
        assert "id" in data
        mock_async.assert_called_once()

    @patch("stt.api.views.async_task")
    def test_create_transcribe_job(self, mock_async, client) -> None:
        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(), "job_type": "transcribe", "model": "large-v3"},
            format="multipart",
        )
        assert response.status_code == 202
        data = response.json()
        assert data["job_type"] == "transcribe"
        assert data["whisper_model"] == "large-v3"
        mock_async.assert_called_once_with(
            "stt.api.tasks.run_transcribe", str(data["id"])
        )

    @patch("stt.api.views.async_task")
    def test_create_job_creates_audit_log(self, mock_async, client) -> None:
        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(), "job_type": "diarize"},
            format="multipart",
        )
        assert response.status_code == 202
        job_id = response.json()["id"]
        audit = AuditLog.objects.filter(
            action=AuditAction.JOB_CREATED,
            resource_id=job_id,
        )
        assert audit.exists()

    def test_create_job_no_file_returns_422(self, client) -> None:
        response = client.post("/v1/jobs", {"job_type": "transcribe"})
        assert response.status_code == 422

    @patch("stt.api.views.async_task")
    def test_create_job_invalid_type_returns_400(self, mock_async, client) -> None:
        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(), "job_type": "invalid"},
            format="multipart",
        )
        assert response.status_code == 400

    @patch("stt.api.views.async_task")
    def test_create_job_unsupported_extension(self, mock_async, client) -> None:
        response = client.post(
            "/v1/jobs",
            {"file": _audio_file(name="test.exe"), "job_type": "transcribe"},
            format="multipart",
        )
        assert response.status_code == 400

    @patch("stt.api.views.async_task")
    def test_create_job_default_type_is_process(self, mock_async, client) -> None:
        response = client.post(
            "/v1/jobs",
            {"file": _audio_file()},
            format="multipart",
        )
        assert response.status_code == 202
        assert response.json()["job_type"] == "process"


@pytest.mark.django_db
class TestJobDetailEndpoint:
    """Tests for GET /v1/jobs/{id}."""

    def test_get_pending_job(self, client) -> None:
        job = Job.objects.create(job_type=JobType.TRANSCRIBE)
        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["status"] == "pending"

    def test_get_completed_job_with_results(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
            result_text="Hello World",
        )
        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result_text"] == "Hello World"

    def test_get_failed_job_with_error(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.DIARIZE,
            status=JobStatus.FAILED,
            error_message="HF token missing",
        )
        response = client.get(f"/v1/jobs/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "HF token missing"

    def test_get_nonexistent_job_returns_404(self, client) -> None:
        fake_id = uuid.uuid4()
        response = client.get(f"/v1/jobs/{fake_id}")
        assert response.status_code == 404

    def test_get_invalid_id_returns_404(self, client) -> None:
        response = client.get("/v1/jobs/not-a-uuid")
        assert response.status_code == 404


# === Task function tests ===


@pytest.mark.django_db
class TestRunTranscribeTask:
    """Tests for the run_transcribe task function."""

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.transcribe_audio")
    def test_transcribe_success(self, mock_transcribe, mock_config) -> None:
        mock_config.return_value = MagicMock(whisper=WhisperConfig())
        mock_transcribe.return_value = "Hello World"

        tmp = Path("/tmp/test_task.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            original_filename=str(tmp),
        )

        run_transcribe(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Hello World"
        assert AuditLog.objects.filter(
            action=AuditAction.JOB_COMPLETED,
            resource_id=str(job.id),
        ).exists()

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.transcribe_audio")
    def test_transcribe_failure(self, mock_transcribe, mock_config) -> None:
        mock_config.return_value = MagicMock(whisper=WhisperConfig())
        mock_transcribe.side_effect = RuntimeError("Model not found")

        tmp = Path("/tmp/test_task_fail.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            original_filename=str(tmp),
        )

        run_transcribe(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.FAILED
        assert "Model not found" in job.error_message

    def test_transcribe_missing_file(self) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            original_filename="/tmp/nonexistent_audio.wav",
        )

        run_transcribe(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.FAILED
        assert "not found" in job.error_message

    def test_transcribe_nonexistent_job(self) -> None:
        fake_id = str(uuid.uuid4())
        # Should not raise
        run_transcribe(fake_id)


@pytest.mark.django_db
class TestRunDiarizeTask:
    """Tests for the run_diarize task function."""

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.format_diarized_segments")
    @patch("stt.api.tasks.diarize_audio")
    def test_diarize_success(self, mock_diarize, mock_format, mock_config) -> None:
        segment = MagicMock()
        segment.speaker = "Sprecher 1"
        segment.start = 0.0
        segment.end = 1.5
        segment.text = "Hallo"
        mock_diarize.return_value = [segment]
        mock_format.return_value = "[Sprecher 1] Hallo"
        mock_config.return_value = MagicMock(
            whisper=WhisperConfig(),
            diarize=DiarizeConfig(hf_token="hf_test"),
        )

        tmp = Path("/tmp/test_diarize.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.DIARIZE,
            original_filename=str(tmp),
        )

        run_diarize(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Hallo"
        assert job.result_diarized_text == "[Sprecher 1] Hallo"
        assert job.result_segments_json is not None
        assert len(job.result_segments_json) == 1


@pytest.mark.django_db
class TestRunProcessTask:
    """Tests for the run_process task function."""

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.process_transcript")
    @patch("stt.api.tasks.transcribe_audio")
    def test_process_without_diarize(
        self, mock_transcribe, mock_process, mock_config
    ) -> None:
        mock_config.return_value = MagicMock(
            whisper=WhisperConfig(),
            diarize=DiarizeConfig(hf_token=""),
            lm_studio=LMStudioConfig(),
        )
        mock_transcribe.return_value = "Hello World"
        mock_process.return_value = ProcessResult(
            diarized_text="",
            structured_text="# Meeting",
            summary="Summary",
        )

        tmp = Path("/tmp/test_process.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.PROCESS,
            original_filename=str(tmp),
            enable_diarize=False,
        )

        run_process(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Hello World"
        assert job.result_structured_text == "# Meeting"
        assert job.result_summary == "Summary"

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.process_transcript")
    @patch("stt.api.tasks.format_diarized_segments")
    @patch("stt.api.tasks.diarize_audio")
    def test_process_with_diarize(
        self, mock_diarize, mock_format, mock_process, mock_config
    ) -> None:
        segment = MagicMock()
        segment.speaker = "SPEAKER_00"
        segment.start = 0.0
        segment.end = 2.0
        segment.text = "Test"
        mock_diarize.return_value = [segment]
        mock_format.return_value = "[SPEAKER_00] Test"
        mock_config.return_value = MagicMock(
            whisper=WhisperConfig(),
            diarize=DiarizeConfig(hf_token="hf_test"),
            lm_studio=LMStudioConfig(),
        )
        mock_process.return_value = ProcessResult(
            diarized_text="[SPEAKER_00] Test",
            structured_text="# Protokoll",
            summary="Zusammenfassung",
        )

        tmp = Path("/tmp/test_process_diarize.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.PROCESS,
            original_filename=str(tmp),
            enable_diarize=True,
        )

        run_process(str(job.id))

        job.refresh_from_db()
        assert job.status == JobStatus.COMPLETED
        assert job.result_text == "Test"
        assert job.result_diarized_text == "[SPEAKER_00] Test"
        assert job.result_structured_text == "# Protokoll"
        assert job.result_summary == "Zusammenfassung"
