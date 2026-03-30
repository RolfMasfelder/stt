"""Tests for the STT Django REST API."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

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
    """Create a simple in-memory file for upload."""
    f = BytesIO(content)
    f.name = name
    return f


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestTranscribeEndpoint:
    """Tests for POST /v1/transcribe."""

    @patch("stt.api.views.transcribe_audio")
    def test_transcribe_success(self, mock_transcribe, client) -> None:
        mock_transcribe.return_value = "Hello World"
        response = client.post(
            "/v1/transcribe",
            {"file": _audio_file(), "model": "small"},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.json() == {"text": "Hello World"}
        mock_transcribe.assert_called_once()

    @patch("stt.api.views.transcribe_audio")
    def test_transcribe_error(self, mock_transcribe, client) -> None:
        from stt.transcribe import TranscriptionError

        mock_transcribe.side_effect = TranscriptionError("fail")
        response = client.post(
            "/v1/transcribe",
            {"file": _audio_file()},
            format="multipart",
        )
        assert response.status_code == 500
        assert "fail" in response.json()["detail"]

    def test_transcribe_no_file_returns_422(self, client) -> None:
        response = client.post("/v1/transcribe")
        assert response.status_code == 422


class TestDiarizeEndpoint:
    """Tests for POST /v1/diarize."""

    @patch("stt.api.views.format_diarized_segments")
    @patch("stt.api.views.diarize_audio")
    def test_diarize_success(self, mock_diarize, mock_format, client) -> None:
        from stt.diarize import DiarizedSegment

        segments = [
            DiarizedSegment(speaker="Sprecher 1", start=0.0, end=1.5, text="Hallo"),
            DiarizedSegment(speaker="Sprecher 2", start=1.5, end=3.0, text="Hi"),
        ]
        mock_diarize.return_value = segments
        mock_format.return_value = "**Sprecher 1:**\nHallo\n\n**Sprecher 2:**\nHi"

        response = client.post(
            "/v1/diarize",
            {"file": _audio_file()},
            format="multipart",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Hallo Hi"
        assert "Sprecher 1" in body["diarized_text"]
        assert len(body["segments"]) == 2
        assert body["segments"][0]["speaker"] == "Sprecher 1"

    @patch("stt.api.views.diarize_audio")
    def test_diarize_error(self, mock_diarize, client) -> None:
        from stt.diarize import DiarizationError

        mock_diarize.side_effect = DiarizationError("no token")
        response = client.post(
            "/v1/diarize",
            {"file": _audio_file()},
            format="multipart",
        )
        assert response.status_code == 500
        assert "no token" in response.json()["detail"]


class TestProcessEndpoint:
    """Tests for POST /v1/process."""

    @patch("stt.api.views.process_transcript")
    @patch("stt.api.views.format_diarized_segments")
    @patch("stt.api.views.diarize_audio")
    def test_process_with_diarize(
        self, mock_diarize, mock_format, mock_process, client
    ) -> None:
        from stt.diarize import DiarizedSegment

        segments = [
            DiarizedSegment(speaker="Sprecher 1", start=0.0, end=2.0, text="Text"),
        ]
        mock_diarize.return_value = segments
        mock_format.return_value = "**Sprecher 1:**\nText"
        mock_process.return_value = ProcessResult(
            structured_text="## Struktur",
            summary="Zusammenfassung",
            diarized_text="**Sprecher 1:**\nText",
        )

        response = client.post(
            "/v1/process",
            {"file": _audio_file(), "diarize": "true"},
            format="multipart",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Text"
        assert body["structured_text"] == "## Struktur"
        assert body["summary"] == "Zusammenfassung"
        assert body["diarized_text"] is not None

    @patch("stt.api.views.process_transcript")
    @patch("stt.api.views.transcribe_audio")
    def test_process_without_diarize(
        self, mock_transcribe, mock_process, client
    ) -> None:
        mock_transcribe.return_value = "Transkript"
        mock_process.return_value = ProcessResult(
            structured_text="Strukturiert",
            summary="Zusammenfassung",
            diarized_text=None,
        )

        response = client.post(
            "/v1/process",
            {"file": _audio_file(), "diarize": "false"},
            format="multipart",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Transkript"
        assert body["structured_text"] == "Strukturiert"
        assert body["summary"] == "Zusammenfassung"

    @patch("stt.api.views.transcribe_audio")
    def test_process_error(self, mock_transcribe, client) -> None:
        from stt.transcribe import TranscriptionError

        mock_transcribe.side_effect = TranscriptionError("boom")
        response = client.post(
            "/v1/process",
            {"file": _audio_file(), "diarize": "false"},
            format="multipart",
        )
        assert response.status_code == 500
        assert "boom" in response.json()["detail"]


class TestUploadValidation:
    """Tests for upload validation (file size, content type)."""

    def test_unsupported_audio_format(self, client) -> None:
        response = client.post(
            "/v1/transcribe",
            {"file": _audio_file("test.txt", b"not audio")},
            format="multipart",
        )
        assert response.status_code == 400
        assert "Unsupported audio format" in response.json()["detail"]

    def test_file_too_large(self, client) -> None:
        with patch("stt.api.views._MAX_UPLOAD_BYTES", 10):
            response = client.post(
                "/v1/transcribe",
                {"file": _audio_file("test.wav", b"x" * 20)},
                format="multipart",
            )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]


class TestDiarizeNoToken:
    """Tests for missing HF token."""

    def test_missing_hf_token_returns_503(self, auth_client) -> None:
        mock_config = MagicMock()
        mock_config.log_level = "WARNING"
        mock_config.whisper = WhisperConfig()
        mock_config.diarize = DiarizeConfig()  # no hf_token
        mock_config.lm_studio = LMStudioConfig()

        with patch("stt.api.views._get_config", return_value=mock_config):
            response = auth_client.post(
                "/v1/diarize",
                {"file": _audio_file()},
                format="multipart",
            )
        assert response.status_code == 503
        assert "HF_STT_TOKEN" in response.json()["detail"]


class TestOpenAPISchema:
    """Tests for OpenAPI schema generation via drf-spectacular."""

    def _get_schema(self, auth_client):
        """Fetch schema using drf-spectacular's SchemaGenerator directly."""
        from drf_spectacular.generators import SchemaGenerator

        generator = SchemaGenerator()
        return generator.get_schema(public=True)

    def test_schema_endpoint_returns_200(self, auth_client) -> None:
        schema = self._get_schema(auth_client)
        assert "openapi" in schema

    def test_schema_has_all_paths(self, auth_client) -> None:
        schema = self._get_schema(auth_client)
        paths = set(schema["paths"].keys())
        expected = {
            "/health",
            "/v1/transcribe",
            "/v1/diarize",
            "/v1/process",
            "/v1/jobs",
            "/v1/jobs/{job_id}",
            "/v1/jobs/{job_id}/correct",
            "/v1/jobs/{job_id}/reprocess",
            "/v1/jobs/{job_id}/versions",
            "/v1/config/storage",
            "/v1/config/storage/{config_id}",
            "/v1/config/storage/{config_id}/test",
        }
        assert expected == paths

    def test_schema_info(self, auth_client) -> None:
        schema = self._get_schema(auth_client)
        assert schema["info"]["title"] == "STT Server API"
        assert schema["info"]["version"] == "1.0.0"

    def test_schema_has_oauth2_security(self, auth_client) -> None:
        schema = self._get_schema(auth_client)
        schemes = schema["components"]["securitySchemes"]
        assert "oauth2" in schemes
        assert "clientCredentials" in schemes["oauth2"]["flows"]
