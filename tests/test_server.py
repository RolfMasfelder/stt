"""Tests for the STT server."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stt.config import DiarizeConfig, LMStudioConfig, WhisperConfig
from stt.summarize import ProcessResult


@pytest.fixture
def client():
    """Create a test client with mocked config."""
    with patch("stt.server.load_config") as mock_config:
        config = MagicMock()
        config.log_level = "WARNING"
        config.whisper = WhisperConfig()
        config.diarize = DiarizeConfig(hf_token="hf_test")
        config.lm_studio = LMStudioConfig()
        mock_config.return_value = config

        from stt.server import app

        with TestClient(app) as tc:
            yield tc


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestTranscribeEndpoint:
    """Tests for POST /v1/transcribe."""

    @patch("stt.server.transcribe_audio")
    def test_transcribe_success(self, mock_transcribe, client) -> None:
        mock_transcribe.return_value = "Hello World"
        response = client.post(
            "/v1/transcribe",
            files={"file": ("test.wav", b"fake audio data", "audio/wav")},
            data={"model": "small"},
        )
        assert response.status_code == 200
        assert response.json() == {"text": "Hello World"}
        mock_transcribe.assert_called_once()

    @patch("stt.server.transcribe_audio")
    def test_transcribe_error(self, mock_transcribe, client) -> None:
        from stt.transcribe import TranscriptionError

        mock_transcribe.side_effect = TranscriptionError("fail")
        response = client.post(
            "/v1/transcribe",
            files={"file": ("test.wav", b"fake", "audio/wav")},
        )
        assert response.status_code == 500
        assert "fail" in response.json()["detail"]

    def test_transcribe_no_file_returns_422(self, client) -> None:
        response = client.post("/v1/transcribe")
        assert response.status_code == 422


class TestDiarizeEndpoint:
    """Tests for POST /v1/diarize."""

    @patch("stt.server.format_diarized_segments")
    @patch("stt.server.diarize_audio")
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
            files={"file": ("test.wav", b"fake", "audio/wav")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Hallo Hi"
        assert "Sprecher 1" in body["diarized_text"]
        assert len(body["segments"]) == 2
        assert body["segments"][0]["speaker"] == "Sprecher 1"

    @patch("stt.server.diarize_audio")
    def test_diarize_error(self, mock_diarize, client) -> None:
        from stt.diarize import DiarizationError

        mock_diarize.side_effect = DiarizationError("no token")
        response = client.post(
            "/v1/diarize",
            files={"file": ("test.wav", b"fake", "audio/wav")},
        )
        assert response.status_code == 500
        assert "no token" in response.json()["detail"]


class TestProcessEndpoint:
    """Tests for POST /v1/process."""

    @patch("stt.server.process_transcript")
    @patch("stt.server.format_diarized_segments")
    @patch("stt.server.diarize_audio")
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
            files={"file": ("test.wav", b"fake", "audio/wav")},
            data={"diarize": "true"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Text"
        assert body["structured_text"] == "## Struktur"
        assert body["summary"] == "Zusammenfassung"
        assert body["diarized_text"] is not None

    @patch("stt.server.process_transcript")
    @patch("stt.server.transcribe_audio")
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
            files={"file": ("test.wav", b"fake", "audio/wav")},
            data={"diarize": "false"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Transkript"
        assert body["structured_text"] == "Strukturiert"
        assert body["summary"] == "Zusammenfassung"

    @patch("stt.server.transcribe_audio")
    def test_process_error(self, mock_transcribe, client) -> None:
        from stt.transcribe import TranscriptionError

        mock_transcribe.side_effect = TranscriptionError("boom")
        response = client.post(
            "/v1/process",
            files={"file": ("test.wav", b"fake", "audio/wav")},
            data={"diarize": "false"},
        )
        assert response.status_code == 500
        assert "boom" in response.json()["detail"]
