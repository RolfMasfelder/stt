"""Tests for the transcription module (HTTP client to ML service)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.config import MLServiceConfig
from stt.transcribe import TranscriptionError, transcribe_audio


class TestTranscribeAudio:
    """Tests for transcribe_audio."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for non-existent file."""
        missing_file = tmp_path / "does_not_exist.wav"
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcribe_audio(missing_file)

    @patch("stt.transcribe.requests.post")
    def test_successful_transcription(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should return text from ML service response."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Hallo Welt"}
        mock_post.return_value = mock_response

        result = transcribe_audio(audio_file)
        assert result == "Hallo Welt"
        mock_post.assert_called_once()

    @patch("stt.transcribe.requests.post")
    def test_uses_config(self, mock_post: MagicMock, tmp_path: Path) -> None:
        """Should use ML service URL from config."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": ""}
        mock_post.return_value = mock_response

        config = MLServiceConfig(base_url="http://custom-ml:9000", timeout=300)
        transcribe_audio(audio_file, config, model="large-v3")

        call_args = mock_post.call_args
        assert "http://custom-ml:9000/v1/transcribe" == call_args[0][0]
        assert call_args[1]["timeout"] == 300

    @patch("stt.transcribe.requests.post")
    def test_transcription_error_on_http_failure(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should wrap HTTP errors in TranscriptionError."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(TranscriptionError, match="ML service transcription failed"):
            transcribe_audio(audio_file)

    @patch("stt.transcribe.requests.post")
    def test_transcription_error_on_connection_failure(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should wrap connection errors in TranscriptionError."""
        import requests

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_post.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(TranscriptionError, match="Failed to connect to ML service"):
            transcribe_audio(audio_file)

    @patch("stt.transcribe.requests.post")
    def test_default_config(self, mock_post: MagicMock, tmp_path: Path) -> None:
        """Should use default config when none provided."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "test"}
        mock_post.return_value = mock_response

        transcribe_audio(audio_file)

        call_args = mock_post.call_args
        assert "http://stt-ml:8091/v1/transcribe" == call_args[0][0]

    @patch("stt.transcribe.requests.post")
    def test_empty_response(self, mock_post: MagicMock, tmp_path: Path) -> None:
        """Should handle empty text in response."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": ""}
        mock_post.return_value = mock_response

        result = transcribe_audio(audio_file)
        assert result == ""
