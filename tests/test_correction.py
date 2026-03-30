"""Tests for correction workflow: PATCH /correct, POST /reprocess, GET /versions."""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.api.models import (
    AuditAction,
    AuditLog,
    Job,
    JobStatus,
    JobType,
    ResultVersion,
)
from stt.api.tasks import run_process, run_transcribe
from stt.config import DiarizeConfig, LMStudioConfig, WhisperConfig
from stt.summarize import ProcessResult


@pytest.fixture
def client(auth_client):
    """Authenticated client with mocked ML config."""
    mock_config = MagicMock()
    mock_config.log_level = "WARNING"
    mock_config.whisper = WhisperConfig()
    mock_config.diarize = DiarizeConfig(hf_token="hf_test")
    mock_config.lm_studio = LMStudioConfig()

    with patch("stt.api.views._get_config", return_value=mock_config):
        yield auth_client


@pytest.fixture
def completed_job(db) -> Job:
    """A completed Job with all result fields populated."""
    job = Job.objects.create(
        job_type=JobType.PROCESS,
        status=JobStatus.COMPLETED,
        result_text="Original text",
        result_diarized_text="[Sprecher 1] Original text",
        result_structured_text="# Original structure",
        result_summary="Original summary",
    )
    ResultVersion.objects.create(
        job=job,
        version=0,
        result_text=job.result_text,
        result_diarized_text=job.result_diarized_text,
        result_structured_text=job.result_structured_text,
        result_summary=job.result_summary,
        source="pipeline",
    )
    return job


# === PATCH /v1/jobs/{id}/correct ===


@pytest.mark.django_db
class TestJobCorrect:
    def test_correct_single_field(self, client, completed_job) -> None:
        response = client.patch(
            f"/v1/jobs/{completed_job.id}/correct",
            {"result_text": "Corrected text"},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_text"] == "Corrected text"
        assert data["result_summary"] == "Original summary"

    def test_correct_creates_version(self, client, completed_job) -> None:
        client.patch(
            f"/v1/jobs/{completed_job.id}/correct",
            {"result_text": "Fixed text"},
            format="json",
        )
        versions = ResultVersion.objects.filter(job=completed_job).order_by("version")
        assert versions.count() == 2
        v1 = versions.last()
        assert v1.version == 1
        assert v1.source == "correction"
        assert v1.result_text == "Fixed text"

    def test_correct_multiple_fields(self, client, completed_job) -> None:
        response = client.patch(
            f"/v1/jobs/{completed_job.id}/correct",
            {
                "result_text": "New text",
                "result_summary": "New summary",
            },
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_text"] == "New text"
        assert data["result_summary"] == "New summary"
        assert data["result_structured_text"] == "# Original structure"

    def test_correct_creates_audit_log(self, client, completed_job) -> None:
        client.patch(
            f"/v1/jobs/{completed_job.id}/correct",
            {"result_text": "Audit text"},
            format="json",
        )
        assert AuditLog.objects.filter(
            action=AuditAction.JOB_UPDATED,
            resource_id=str(completed_job.id),
        ).exists()

    def test_correct_no_fields_returns_400(self, client, completed_job) -> None:
        response = client.patch(
            f"/v1/jobs/{completed_job.id}/correct",
            {},
            format="json",
        )
        assert response.status_code == 400

    def test_correct_nonexistent_job_returns_404(self, client) -> None:
        response = client.patch(
            f"/v1/jobs/{uuid.uuid4()}/correct",
            {"result_text": "X"},
            format="json",
        )
        assert response.status_code == 404


# === POST /v1/jobs/{id}/reprocess ===


@pytest.mark.django_db
class TestJobReprocess:
    @patch("stt.api.views.structure_text", return_value="# New structure")
    def test_reprocess_structure(self, mock_struct, client, completed_job) -> None:
        response = client.post(
            f"/v1/jobs/{completed_job.id}/reprocess",
            {"steps": ["structure"]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_structured_text"] == "# New structure"
        assert data["result_summary"] == "Original summary"
        mock_struct.assert_called_once()

    @patch("stt.api.views.summarize_text", return_value="New summary")
    def test_reprocess_summarize(self, mock_summ, client, completed_job) -> None:
        response = client.post(
            f"/v1/jobs/{completed_job.id}/reprocess",
            {"steps": ["summarize"]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_summary"] == "New summary"
        mock_summ.assert_called_once()

    @patch("stt.api.views.summarize_text", return_value="Both summary")
    @patch("stt.api.views.structure_text", return_value="# Both structure")
    def test_reprocess_both_steps(
        self, mock_struct, mock_summ, client, completed_job
    ) -> None:
        response = client.post(
            f"/v1/jobs/{completed_job.id}/reprocess",
            {"steps": ["structure", "summarize"]},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result_structured_text"] == "# Both structure"
        assert data["result_summary"] == "Both summary"

    def test_reprocess_creates_version(self, client, completed_job) -> None:
        with patch("stt.api.views.structure_text", return_value="# V"):
            client.post(
                f"/v1/jobs/{completed_job.id}/reprocess",
                {"steps": ["structure"]},
                format="json",
            )
        versions = ResultVersion.objects.filter(job=completed_job).order_by("version")
        assert versions.count() == 2
        v1 = versions.last()
        assert v1.source == "reprocess"

    def test_reprocess_creates_audit_log(self, client, completed_job) -> None:
        with patch("stt.api.views.structure_text", return_value="# X"):
            client.post(
                f"/v1/jobs/{completed_job.id}/reprocess",
                {"steps": ["structure"]},
                format="json",
            )
        assert AuditLog.objects.filter(
            action=AuditAction.JOB_REPROCESSED,
            resource_id=str(completed_job.id),
        ).exists()

    def test_reprocess_no_text_returns_400(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.PROCESS,
            status=JobStatus.COMPLETED,
            result_text="",
        )
        response = client.post(
            f"/v1/jobs/{job.id}/reprocess",
            {"steps": ["structure"]},
            format="json",
        )
        assert response.status_code == 400

    def test_reprocess_empty_steps_returns_400(self, client, completed_job) -> None:
        response = client.post(
            f"/v1/jobs/{completed_job.id}/reprocess",
            {"steps": []},
            format="json",
        )
        assert response.status_code == 400

    def test_reprocess_invalid_step_returns_400(self, client, completed_job) -> None:
        response = client.post(
            f"/v1/jobs/{completed_job.id}/reprocess",
            {"steps": ["transcribe"]},
            format="json",
        )
        assert response.status_code == 400

    def test_reprocess_nonexistent_job_returns_404(self, client) -> None:
        response = client.post(
            f"/v1/jobs/{uuid.uuid4()}/reprocess",
            {"steps": ["structure"]},
            format="json",
        )
        assert response.status_code == 404

    @patch(
        "stt.api.views.structure_text",
        side_effect=Exception("LM Studio offline"),
    )
    def test_reprocess_lm_error_returns_500(
        self, mock_struct, client, completed_job
    ) -> None:
        from stt.summarize import SummarizationError

        mock_struct.side_effect = SummarizationError("LM Studio offline")
        response = client.post(
            f"/v1/jobs/{completed_job.id}/reprocess",
            {"steps": ["structure"]},
            format="json",
        )
        assert response.status_code == 500


# === GET /v1/jobs/{id}/versions ===


@pytest.mark.django_db
class TestJobVersionList:
    def test_list_versions(self, client, completed_job) -> None:
        response = client.get(f"/v1/jobs/{completed_job.id}/versions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["version"] == 0
        assert data[0]["source"] == "pipeline"

    def test_versions_after_correction(self, client, completed_job) -> None:
        client.patch(
            f"/v1/jobs/{completed_job.id}/correct",
            {"result_text": "Fixed text"},
            format="json",
        )
        response = client.get(f"/v1/jobs/{completed_job.id}/versions")
        data = response.json()
        assert len(data) == 2
        assert data[0]["version"] == 0
        assert data[1]["version"] == 1
        assert data[1]["result_text"] == "Fixed text"

    def test_versions_nonexistent_job_returns_404(self, client) -> None:
        response = client.get(f"/v1/jobs/{uuid.uuid4()}/versions")
        assert response.status_code == 404

    def test_empty_versions(self, client) -> None:
        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            status=JobStatus.COMPLETED,
        )
        response = client.get(f"/v1/jobs/{job.id}/versions")
        assert response.status_code == 200
        assert response.json() == []


# === Task creates initial version ===


@pytest.mark.django_db
class TestTaskCreatesVersion:
    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.transcribe_audio")
    def test_run_transcribe_creates_v0(self, mock_transcribe, mock_config) -> None:
        mock_config.return_value = MagicMock(whisper=WhisperConfig())
        mock_transcribe.return_value = "Hello World"

        tmp = Path("/tmp/test_correction_task.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.TRANSCRIBE,
            original_filename=str(tmp),
        )

        run_transcribe(str(job.id))

        versions = ResultVersion.objects.filter(job=job)
        assert versions.count() == 1
        v0 = versions.first()
        assert v0.version == 0
        assert v0.source == "pipeline"
        assert v0.result_text == "Hello World"

    @patch("stt.api.tasks._get_config")
    @patch("stt.api.tasks.process_transcript")
    @patch("stt.api.tasks.transcribe_audio")
    def test_run_process_creates_v0(
        self, mock_transcribe, mock_process, mock_config
    ) -> None:
        mock_config.return_value = MagicMock(
            whisper=WhisperConfig(),
            diarize=DiarizeConfig(hf_token=""),
            lm_studio=LMStudioConfig(),
        )
        mock_transcribe.return_value = "Some text"
        mock_process.return_value = ProcessResult(
            diarized_text="",
            structured_text="# Structure",
            summary="Summary",
        )

        tmp = Path("/tmp/test_correction_process.wav")
        tmp.write_bytes(b"audio")

        job = Job.objects.create(
            job_type=JobType.PROCESS,
            original_filename=str(tmp),
            enable_diarize=False,
        )

        run_process(str(job.id))

        versions = ResultVersion.objects.filter(job=job)
        assert versions.count() == 1
        v0 = versions.first()
        assert v0.version == 0
        assert v0.result_text == "Some text"
        assert v0.result_structured_text == "# Structure"
        assert v0.result_summary == "Summary"
