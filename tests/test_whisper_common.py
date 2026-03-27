"""Tests for the whisper_common module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.whisper_common import convert_to_whisper_format


class TestConvertToWhisperFormat:
    """Tests for convert_to_whisper_format."""

    @patch("stt.whisper_common.subprocess.run")
    def test_skips_conversion_when_already_native(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        probe_result = MagicMock()
        probe_result.stdout = "pcm_s16le,16000,1\n"
        mock_run.return_value = probe_result

        result = convert_to_whisper_format(audio_file)

        assert result == audio_file
        mock_run.assert_called_once()  # only ffprobe, no ffmpeg

    @patch("stt.whisper_common.subprocess.run")
    def test_converts_when_different_format(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio" * 1000)

        converted_file = tmp_path / "test.whisper.wav"
        converted_file.write_bytes(b"converted" * 100)

        probe_result = MagicMock()
        probe_result.stdout = "pcm_s16le,48000,2\n"

        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "ffprobe":
                return probe_result
            return MagicMock()  # ffmpeg

        mock_run.side_effect = side_effect

        result = convert_to_whisper_format(audio_file)

        assert result == converted_file
        assert mock_run.call_count == 2  # ffprobe + ffmpeg

    @patch("stt.whisper_common.subprocess.run")
    def test_converts_when_probe_fails(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        import subprocess

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio" * 1000)

        converted_file = tmp_path / "test.whisper.wav"
        converted_file.write_bytes(b"converted" * 100)

        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "ffprobe":
                raise subprocess.CalledProcessError(1, cmd, stderr="probe error")
            return MagicMock()

        mock_run.side_effect = side_effect

        result = convert_to_whisper_format(audio_file)

        assert result == converted_file

    @patch("stt.whisper_common.subprocess.run")
    def test_raises_on_ffmpeg_failure(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        import subprocess

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        probe_result = MagicMock()
        probe_result.stdout = "pcm_s16le,48000,2\n"

        def side_effect(*args, **kwargs):
            cmd = args[0]
            if cmd[0] == "ffprobe":
                return probe_result
            raise subprocess.CalledProcessError(1, cmd, stderr="conversion failed")

        mock_run.side_effect = side_effect

        with pytest.raises(RuntimeError, match="ffmpeg conversion failed"):
            convert_to_whisper_format(audio_file)
