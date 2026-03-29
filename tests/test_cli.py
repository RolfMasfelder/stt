"""Integration tests for the CLI entry point."""

from unittest.mock import MagicMock, patch

from stt.__main__ import main
from stt.summarize import ProcessResult


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
        config.stt_server_url = None
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
        config.stt_server_url = None
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
        config.stt_server_url = None
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
        config.stt_server_url = None
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
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_transcribe.return_value = "Transkript"
        mock_process.return_value = ProcessResult(
            structured_text="## Struktur",
            summary="Zusammenfassung",
            diarized_text=None,
        )

        result = main([str(audio_file), "--process"])
        assert result == 0
        mock_process.assert_called_once_with(
            "Transkript",
            config.lm_studio,
            diarize=False,
            diarized_text=None,
        )

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
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_transcribe.return_value = "Transkript"
        mock_process.return_value = ProcessResult(
            structured_text="Strukturiert",
            summary="Zusammenfassung",
            diarized_text=None,
        )

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

    @patch("stt.__main__.load_config")
    def test_skip_without_text_file_returns_1(
        self, mock_config: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should return 1 when --skip is used without --text-file."""
        config = MagicMock()
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config

        result = main(["--skip"])
        assert result == 1

    @patch("stt.__main__.load_config")
    def test_skip_with_missing_text_file_returns_1(
        self, mock_config: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should return 1 when --text-file points to a non-existent file."""
        config = MagicMock()
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config

        result = main(["--skip", "--text-file", str(tmp_path / "missing.txt")])
        assert result == 1

    @patch("stt.__main__.load_config")
    def test_skip_reads_text_file(
        self, mock_config: MagicMock, tmp_path: MagicMock
    ) -> None:
        """Should read transcript from text file when --skip --text-file is used."""
        text_file = tmp_path / "transcript.txt"
        text_file.write_text("Existing transcript text", encoding="utf-8")
        output_file = tmp_path / "output.txt"

        config = MagicMock()
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config

        result = main(["--skip", "--text-file", str(text_file), "-o", str(output_file)])
        assert result == 0
        assert output_file.read_text() == "Existing transcript text"

    @patch("stt.__main__.process_transcript")
    @patch("stt.__main__.load_config")
    def test_skip_with_process(
        self,
        mock_config: MagicMock,
        mock_process: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """Should run full pipeline from text file with --skip --text-file --process."""
        text_file = tmp_path / "transcript.txt"
        text_file.write_text("Meeting transcript", encoding="utf-8")

        config = MagicMock()
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_process.return_value = ProcessResult(
            structured_text="Strukturiert",
            summary="Zusammenfassung",
            diarized_text=None,
        )

        result = main(["--skip", "--text-file", str(text_file), "--process"])
        assert result == 0
        mock_process.assert_called_once_with(
            "Meeting transcript",
            config.lm_studio,
            diarize=False,
            diarized_text=None,
        )

    @patch("stt.__main__.diarize_text")
    @patch("stt.__main__.load_config")
    def test_skip_with_diarize(
        self,
        mock_config: MagicMock,
        mock_diarize: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """Should run diarization from text file with --skip --text-file --diarize."""
        text_file = tmp_path / "transcript.txt"
        text_file.write_text("Speaker text here", encoding="utf-8")

        config = MagicMock()
        config.stt_server_url = None
        config.log_level = "WARNING"
        config.audio_input_dir = tmp_path
        mock_config.return_value = config
        mock_diarize.return_value = "Speaker 1: text"

        result = main(["--skip", "--text-file", str(text_file), "--diarize"])
        assert result == 0
        mock_diarize.assert_called_once_with("Speaker text here", config.lm_studio)


class TestCLIServerUrl:
    """Tests for --server-url and --ca-cert CLI flags."""

    @patch("stt.__main__.STTClient")
    @patch("stt.__main__.load_config")
    def test_server_url_overrides_config(
        self,
        mock_config: MagicMock,
        mock_client_cls: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """--server-url should override STT_SERVER_URL from env."""
        from stt.config import AppConfig

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")

        config = AppConfig(
            stt_server_url="http://old-server:8000",
            audio_input_dir=tmp_path,
        )
        mock_config.return_value = config

        mock_client = MagicMock()
        mock_client.transcribe.return_value = "text"
        mock_client_cls.return_value = mock_client

        result = main([str(audio_file), "--server-url", "https://new-server:9000"])
        assert result == 0
        mock_client_cls.assert_called_once()
        call_args = mock_client_cls.call_args
        assert call_args[0][0] == "https://new-server:9000"

    @patch("stt.__main__.STTClient")
    @patch("stt.__main__.load_config")
    def test_ca_cert_passed_to_client(
        self,
        mock_config: MagicMock,
        mock_client_cls: MagicMock,
        tmp_path: MagicMock,
    ) -> None:
        """--ca-cert should be passed as verify parameter to STTClient."""
        from stt.config import AppConfig

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("fake ca cert", encoding="utf-8")

        config = AppConfig(
            stt_server_url="https://server:8000",
            audio_input_dir=tmp_path,
        )
        mock_config.return_value = config

        mock_client = MagicMock()
        mock_client.transcribe.return_value = "text"
        mock_client_cls.return_value = mock_client

        result = main(
            [
                str(audio_file),
                "--ca-cert",
                str(ca_file),
            ]
        )
        assert result == 0
        call_kwargs = mock_client_cls.call_args[1]
        assert call_kwargs["verify"] == str(ca_file)

    def test_parse_server_url_flag(self) -> None:
        """parse_args should accept --server-url."""
        from stt.__main__ import parse_args

        args = parse_args(["--server-url", "https://example.com"])
        assert args.server_url == "https://example.com"

    def test_parse_ca_cert_flag(self) -> None:
        """parse_args should accept --ca-cert."""
        from stt.__main__ import parse_args

        args = parse_args(["--ca-cert", "/path/to/ca.pem"])
        assert str(args.ca_cert) == "/path/to/ca.pem"
