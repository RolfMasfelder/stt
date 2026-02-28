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

    @patch("stt.transcribe.WhisperModel")
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

    @patch("stt.transcribe.WhisperModel")
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

    @patch("stt.transcribe.WhisperModel")
    def test_transcription_error(
        self, mock_model_class: MagicMock, tmp_path: Path
    ) -> None:
        """Should wrap exceptions in TranscriptionError."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio data")

        mock_model_class.side_effect = RuntimeError("Model load failed")

        with pytest.raises(TranscriptionError, match="Failed to transcribe"):
            transcribe_audio(audio_file)

    @patch("stt.transcribe.WhisperModel")
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
