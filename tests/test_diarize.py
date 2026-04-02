"""Tests for the speaker diarization module (HTTP client to ML service)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.config import MLServiceConfig
from stt.diarize import (
    DiarizationError,
    DiarizedSegment,
    diarize_audio,
    format_diarized_segments,
)


class TestFormatDiarizedSegments:
    """Tests for format_diarized_segments."""

    def test_empty_segments(self) -> None:
        assert format_diarized_segments([]) == ""

    def test_single_segment(self) -> None:
        segments = [DiarizedSegment("Sprecher 1", 0.0, 5.0, "Hallo Welt")]
        result = format_diarized_segments(segments)
        assert result == "**Sprecher 1:**\nHallo Welt"

    def test_merge_consecutive_same_speaker(self) -> None:
        segments = [
            DiarizedSegment("Sprecher 1", 0.0, 2.0, "Hallo"),
            DiarizedSegment("Sprecher 1", 2.0, 5.0, "Welt"),
        ]
        result = format_diarized_segments(segments)
        assert result == "**Sprecher 1:**\nHallo Welt"

    def test_different_speakers(self) -> None:
        segments = [
            DiarizedSegment("Sprecher 1", 0.0, 3.0, "Hallo"),
            DiarizedSegment("Sprecher 2", 3.0, 6.0, "Hi zurück"),
            DiarizedSegment("Sprecher 1", 6.0, 9.0, "Wie gehts?"),
        ]
        result = format_diarized_segments(segments)
        assert "**Sprecher 1:**\nHallo" in result
        assert "**Sprecher 2:**\nHi zurück" in result
        assert "**Sprecher 1:**\nWie gehts?" in result


class TestDiarizeAudio:
    """Tests for diarize_audio (HTTP client)."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            diarize_audio(tmp_path / "missing.wav")

    @patch("stt.diarize.requests.post")
    def test_successful_diarization(self, mock_post: MagicMock, tmp_path: Path) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "text": "Hallo zusammen Guten Morgen",
            "diarized_text": "**Sprecher 1:**\nHallo zusammen\n\n**Sprecher 2:**\nGuten Morgen",
            "segments": [
                {
                    "speaker": "Sprecher 1",
                    "start": 0.0,
                    "end": 3.0,
                    "text": "Hallo zusammen",
                },
                {
                    "speaker": "Sprecher 2",
                    "start": 3.0,
                    "end": 6.0,
                    "text": "Guten Morgen",
                },
            ],
        }
        mock_post.return_value = mock_response

        result = diarize_audio(audio_file)

        assert len(result) == 2
        assert result[0].speaker == "Sprecher 1"
        assert result[0].text == "Hallo zusammen"
        assert result[1].speaker == "Sprecher 2"
        assert result[1].text == "Guten Morgen"

    @patch("stt.diarize.requests.post")
    def test_uses_config(self, mock_post: MagicMock, tmp_path: Path) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"segments": []}
        mock_post.return_value = mock_response

        config = MLServiceConfig(base_url="http://custom-ml:9000", timeout=300)
        diarize_audio(audio_file, config, model="large-v3")

        call_args = mock_post.call_args
        assert "http://custom-ml:9000/v1/diarize" == call_args[0][0]
        assert call_args[1]["timeout"] == 300

    @patch("stt.diarize.requests.post")
    def test_hf_token_not_configured(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "HF_STT_TOKEN not configured"
        mock_post.return_value = mock_response

        with pytest.raises(DiarizationError, match="HF_STT_TOKEN not configured"):
            diarize_audio(audio_file)

    @patch("stt.diarize.requests.post")
    def test_http_error(self, mock_post: MagicMock, tmp_path: Path) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(DiarizationError, match="ML service diarization failed"):
            diarize_audio(audio_file)

    @patch("stt.diarize.requests.post")
    def test_connection_error(self, mock_post: MagicMock, tmp_path: Path) -> None:
        import requests

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_post.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(DiarizationError, match="Failed to connect to ML service"):
            diarize_audio(audio_file)
