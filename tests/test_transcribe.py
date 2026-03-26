"""Tests for the transcription module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.config import WhisperConfig
from stt.transcribe import TranscriptionError, transcribe_audio


class TestTranscribeAudio:
    """Tests for transcribe_audio."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for non-existent file."""
        missing_file = tmp_path / "does_not_exist.wav"
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            transcribe_audio(missing_file)

    @patch("stt.whisper_common.WhisperModel")
    def test_empty_audio_file(
        self, mock_model_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should handle empty audio file (0 bytes) gracefully."""
        audio_file = tmp_path / "empty.wav"
        audio_file.write_bytes(b"")

        mock_info = MagicMock()
        mock_info.language = "de"
        mock_info.language_probability = 0.0

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)
        mock_model_class.return_value = mock_model

        result = transcribe_audio(audio_file)
        assert result == ""

    @patch("stt.whisper_common.WhisperModel")
    def test_successful_transcription(
        self, mock_model_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should return joined segment text."""
        # Create a fake audio file
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        # Mock segments
        seg1 = MagicMock()
        seg1.text = "Hallo"
        seg2 = MagicMock()
        seg2.text = "Welt"

        mock_info = MagicMock()
        mock_info.language = "de"
        mock_info.language_probability = 0.95

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([seg1, seg2], mock_info)
        mock_model_class.return_value = mock_model

        result = transcribe_audio(audio_file)
        assert result == "Hallo Welt"

    @patch("stt.whisper_common.WhisperModel")
    def test_uses_config(self, mock_model_class: MagicMock, tmp_path: Path) -> None:
        """Should pass config values to WhisperModel."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_info = MagicMock()
        mock_info.language = "de"
        mock_info.language_probability = 0.9

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)
        mock_model_class.return_value = mock_model

        config = WhisperConfig(model_name="large-v3", device="cuda")
        transcribe_audio(audio_file, config)

        mock_model_class.assert_called_once_with("large-v3", device="cuda")

    @patch("stt.whisper_common.WhisperModel")
    def test_transcription_error(
        self, mock_model_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should wrap exceptions in TranscriptionError."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_model_class.side_effect = RuntimeError("Model load failed")

        with pytest.raises(TranscriptionError, match="Failed to transcribe"):
            transcribe_audio(audio_file)

    @patch("stt.whisper_common.WhisperModel")
    def test_default_config(self, mock_model_class: MagicMock, tmp_path: Path) -> None:
        """Should use default config when none provided."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_info = MagicMock()
        mock_info.language = "de"
        mock_info.language_probability = 0.9

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)
        mock_model_class.return_value = mock_model

        transcribe_audio(audio_file)
        mock_model_class.assert_called_once_with("small", device="cpu")


class TestRemoteTranscription:
    """Tests for remote transcription via faster-whisper-server."""

    @patch("stt.whisper_common.requests.post")
    def test_remote_transcription_success(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should send audio to remote API and return transcript."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "  Hallo Welt  "
        mock_post.return_value = mock_response

        config = WhisperConfig(
            api_url="http://192.168.178.80:8000/v1/audio/transcriptions"
        )
        result = transcribe_audio(audio_file, config)

        assert result == "Hallo Welt"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["data"]["model"] == "small"
        assert call_kwargs.kwargs["data"]["response_format"] == "text"

    @patch("stt.whisper_common.requests.post")
    def test_remote_transcription_appends_endpoint(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should append /v1/audio/transcriptions if not present."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        config = WhisperConfig(api_url="http://192.168.178.80:8000")
        transcribe_audio(audio_file, config)

        called_url = mock_post.call_args.args[0]
        assert called_url == "http://192.168.178.80:8000/v1/audio/transcriptions"

    @patch("stt.whisper_common.requests.post")
    def test_remote_transcription_keeps_full_endpoint(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should not duplicate endpoint path if already present."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        config = WhisperConfig(
            api_url="http://192.168.178.80:8000/v1/audio/transcriptions"
        )
        transcribe_audio(audio_file, config)

        called_url = mock_post.call_args.args[0]
        assert called_url == "http://192.168.178.80:8000/v1/audio/transcriptions"

    @patch("stt.whisper_common.requests.post")
    def test_remote_transcription_http_error(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should raise TranscriptionError on non-200 response."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        config = WhisperConfig(api_url="http://192.168.178.80:8000")
        with pytest.raises(TranscriptionError, match="HTTP 500"):
            transcribe_audio(audio_file, config)

    @patch("stt.whisper_common.requests.post")
    def test_remote_transcription_connection_error(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should raise TranscriptionError on connection failure."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_post.side_effect = ConnectionError("Connection refused")

        config = WhisperConfig(api_url="http://192.168.178.80:8000")
        with pytest.raises(TranscriptionError, match="Failed to transcribe"):
            transcribe_audio(audio_file, config)

    @patch("stt.whisper_common.WhisperModel")
    def test_no_api_url_uses_local(
        self, mock_model_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should fall back to local transcription when api_url is None."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_info = MagicMock()
        mock_info.language = "de"
        mock_info.language_probability = 0.9

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)
        mock_model_class.return_value = mock_model

        config = WhisperConfig(api_url=None)
        transcribe_audio(audio_file, config)

        mock_model_class.assert_called_once_with("small", device="cpu")

    @patch("stt.whisper_common.requests.post")
    def test_remote_uses_custom_model_name(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        """Should send configured model name to remote API."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        config = WhisperConfig(
            model_name="large-v3",
            api_url="http://192.168.178.80:8000",
        )
        transcribe_audio(audio_file, config)

        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["data"]["model"] == "large-v3"
