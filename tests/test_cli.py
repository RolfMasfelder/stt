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

    @patch("stt.__main__.process_transcript")
    @patch("stt.__main__.transcribe_audio")
    @patch("stt.__main__.load_config")
    def test_process_flag(
        self,
        mock_config: MagicMock,
        mock_transcribe: MagicMock,
        mock_process: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """Should run full pipeline with --process."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")

        config = MagicMock()
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_transcribe.return_value = "Transkript"
        mock_process.return_value = ("## Struktur", "Zusammenfassung")

        result = main([str(audio_file), "--process"])
        assert result == 0
        mock_process.assert_called_once_with("Transkript", config.lm_studio)

    @patch("stt.__main__.process_transcript")
    @patch("stt.__main__.transcribe_audio")
    @patch("stt.__main__.load_config")
    def test_process_saves_files(
        self,
        mock_config: MagicMock,
        mock_transcribe: MagicMock,
        mock_process: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """Should save structure and summary files with --process --output."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")
        output_file = tmp_path / "result.txt"

        config = MagicMock()
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_transcribe.return_value = "Transkript"
        mock_process.return_value = ("Strukturiert", "Zusammenfassung")

        result = main([str(audio_file), "--process", "-o", str(output_file)])
        assert result == 0

        # Transcript written to main output
        assert output_file.read_text() == "Transkript"
        # Structure + summary written as separate files
        assert (tmp_path / "result_struktur.md").read_text() == "Strukturiert"
        assert (tmp_path / "result_zusammenfassung.md").read_text() == "Zusammenfassung"

    @patch("stt.__main__.transcribe_audio")
    @patch("stt.__main__.load_config")
    def test_timeout_override(
        self,
        mock_config: MagicMock,
        mock_transcribe: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """Should override LM Studio timeout from CLI --timeout."""
        from stt.config import AppConfig, LMStudioConfig, WhisperConfig

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")

        config = AppConfig(
            lm_studio=LMStudioConfig(timeout=120),
            whisper=WhisperConfig(),
        )
        mock_config.return_value = config
        mock_transcribe.return_value = "Hello"

        with patch("stt.__main__.summarize_text") as mock_summarize:
            mock_summarize.return_value = "Summary"
            result = main([str(audio_file), "--summarize", "--timeout", "900"])

        assert result == 0
        # The config passed to summarize_text should have timeout=900
        called_config = mock_summarize.call_args.args[1]
        assert called_config.timeout == 900
