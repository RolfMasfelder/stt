"""Integration tests for the CLI entry point."""

from unittest.mock import MagicMock, patch

from stt.__main__ import main


class TestCLI:
    """Tests for the CLI main function."""

    @patch("stt.__main__.transcribe_audio")
    @patch("stt.__main__.load_config")
    def test_transcribe_file(
        self, mock_config: MagicMock, mock_transcribe: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should transcribe a given audio file."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")

        config = MagicMock()
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_transcribe.return_value = "Hello World"

        result = main([str(audio_file)])
        assert result == 0
        mock_transcribe.assert_called_once()

    @patch("stt.__main__.transcribe_audio")
    @patch("stt.__main__.load_config")
    def test_missing_audio_file(
        self, mock_config: MagicMock, mock_transcribe: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should return 1 when no audio files are found."""
        config = MagicMock()
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path

        mock_config.return_value = config

        result = main([])
        assert result == 1

    @patch("stt.__main__.transcribe_audio")
    @patch("stt.__main__.load_config")
    def test_output_to_file(
        self, mock_config: MagicMock, mock_transcribe: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should write transcript to file with --output."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")
        output_file = tmp_path / "transcript.txt"

        config = MagicMock()
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_transcribe.return_value = "Transcribed text"

        result = main([str(audio_file), "--output", str(output_file)])
        assert result == 0
        assert output_file.read_text() == "Transcribed text"

    @patch("stt.__main__.load_config")
    def test_transcription_error_returns_1(
        self, mock_config: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should return 1 when transcription fails."""
        from stt.transcribe import TranscriptionError

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")

        config = MagicMock()
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config

        with patch(
            "stt.__main__.transcribe_audio",
            side_effect=TranscriptionError("fail"),
        ):
            result = main([str(audio_file)])
            assert result == 1
