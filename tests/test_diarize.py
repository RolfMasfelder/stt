"""Tests for the speaker diarization module."""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stt.config import DiarizeConfig, WhisperConfig
from stt.diarize import (
    DiarizationError,
    DiarizedSegment,
    _assign_speaker,
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


class TestAssignSpeaker:
    """Tests for _assign_speaker."""

    def test_single_speaker_overlap(self) -> None:
        @dataclass
        class Turn:
            start: float
            end: float

        diarization = MagicMock()
        diarization.itertracks.return_value = [
            (Turn(0.0, 5.0), None, "SPEAKER_00"),
        ]
        assert _assign_speaker(1.0, 3.0, diarization) == "SPEAKER_00"

    def test_no_overlap(self) -> None:
        diarization = MagicMock()
        diarization.itertracks.return_value = []
        assert _assign_speaker(0.0, 1.0, diarization) == "UNKNOWN"

    def test_majority_speaker(self) -> None:
        @dataclass
        class Turn:
            start: float
            end: float

        diarization = MagicMock()
        # segment [1, 5]: SPEAKER_00 covers [0, 2.5] → 1.5s overlap
        #                  SPEAKER_01 covers [2.5, 7] → 2.5s overlap
        diarization.itertracks.return_value = [
            (Turn(0.0, 2.5), None, "SPEAKER_00"),
            (Turn(2.5, 7.0), None, "SPEAKER_01"),
        ]
        assert _assign_speaker(1.0, 5.0, diarization) == "SPEAKER_01"


class TestDiarizeAudio:
    """Tests for diarize_audio."""

    def test_missing_token(self, tmp_path: Path) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake")
        config = DiarizeConfig(hf_token=None)
        with pytest.raises(DiarizationError, match="HuggingFace token required"):
            diarize_audio(audio_file, WhisperConfig(), config)

    def test_file_not_found(self, tmp_path: Path) -> None:
        config = DiarizeConfig(hf_token="fake-token")
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            diarize_audio(tmp_path / "missing.wav", WhisperConfig(), config)

    @patch("stt.diarize._run_diarization")
    @patch("stt.diarize._get_whisper_segments_local")
    def test_local_diarization(
        self, mock_whisper: MagicMock, mock_diarize: MagicMock, tmp_path: Path
    ) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_whisper.return_value = [
            (0.0, 3.0, "Hallo zusammen"),
            (3.0, 6.0, "Guten Morgen"),
        ]

        @dataclass
        class Turn:
            start: float
            end: float

        mock_diarize.return_value = MagicMock()
        mock_diarize.return_value.itertracks.return_value = [
            (Turn(0.0, 3.5), None, "SPEAKER_00"),
            (Turn(3.5, 7.0), None, "SPEAKER_01"),
        ]

        config = DiarizeConfig(hf_token="fake-token")
        result = diarize_audio(audio_file, WhisperConfig(), config)

        assert len(result) == 2
        assert result[0].speaker == "Sprecher 1"
        assert result[0].text == "Hallo zusammen"
        assert result[1].speaker == "Sprecher 2"
        assert result[1].text == "Guten Morgen"

    @patch("stt.diarize._run_diarization")
    @patch("stt.diarize._get_whisper_segments_remote")
    def test_remote_diarization(
        self, mock_whisper: MagicMock, mock_diarize: MagicMock, tmp_path: Path
    ) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_whisper.return_value = [
            (0.0, 5.0, "Test text"),
        ]

        @dataclass
        class Turn:
            start: float
            end: float

        mock_diarize.return_value = MagicMock()
        mock_diarize.return_value.itertracks.return_value = [
            (Turn(0.0, 5.0), None, "SPEAKER_00"),
        ]

        whisper_config = WhisperConfig(api_url="http://localhost:8000")
        diarize_config = DiarizeConfig(hf_token="fake-token")
        result = diarize_audio(audio_file, whisper_config, diarize_config)

        assert len(result) == 1
        assert result[0].speaker == "Sprecher 1"
        mock_whisper.assert_called_once()

    @patch("stt.diarize._run_diarization")
    @patch("stt.diarize._get_whisper_segments_local")
    def test_diarization_error_wrapped(
        self, mock_whisper: MagicMock, mock_diarize: MagicMock, tmp_path: Path
    ) -> None:
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_whisper.side_effect = RuntimeError("Model load failed")

        config = DiarizeConfig(hf_token="fake-token")
        with pytest.raises(DiarizationError, match="Failed to diarize"):
            diarize_audio(audio_file, WhisperConfig(), config)

    @patch("stt.diarize._run_diarization")
    @patch("stt.diarize._get_whisper_segments_local")
    def test_speaker_normalization(
        self, mock_whisper: MagicMock, mock_diarize: MagicMock, tmp_path: Path
    ) -> None:
        """Speaker labels should be normalized to 'Sprecher N' format."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_whisper.return_value = [
            (0.0, 2.0, "Eins"),
            (2.0, 4.0, "Zwei"),
            (4.0, 6.0, "Drei"),
        ]

        @dataclass
        class Turn:
            start: float
            end: float

        mock_diarize.return_value = MagicMock()
        mock_diarize.return_value.itertracks.return_value = [
            (Turn(0.0, 2.5), None, "SPEAKER_00"),
            (Turn(2.5, 4.5), None, "SPEAKER_01"),
            (Turn(4.5, 7.0), None, "SPEAKER_00"),
        ]

        config = DiarizeConfig(hf_token="fake-token")
        result = diarize_audio(audio_file, WhisperConfig(), config)

        assert result[0].speaker == "Sprecher 1"
        assert result[1].speaker == "Sprecher 2"
        assert result[2].speaker == "Sprecher 1"


class TestRemoteWhisperSegments:
    """Tests for _get_whisper_segments_remote."""

    @patch("stt.whisper_common.requests.post")
    def test_successful_remote_segments(
        self, mock_post: MagicMock, tmp_path: Path
    ) -> None:
        from stt.diarize import _get_whisper_segments_remote

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "segments": [
                {"start": 0.0, "end": 3.0, "text": " Hallo "},
                {"start": 3.0, "end": 6.0, "text": " Welt "},
            ]
        }
        mock_post.return_value = mock_response

        config = WhisperConfig(api_url="http://localhost:8000")
        result = _get_whisper_segments_remote(audio_file, config)

        assert len(result) == 2
        assert result[0] == (0.0, 3.0, "Hallo")
        assert result[1] == (3.0, 6.0, "Welt")

    @patch("stt.whisper_common.requests.post")
    def test_remote_http_error(self, mock_post: MagicMock, tmp_path: Path) -> None:
        from stt.diarize import _get_whisper_segments_remote

        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake audio")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_post.return_value = mock_response

        config = WhisperConfig(api_url="http://localhost:8000")
        with pytest.raises(DiarizationError, match="HTTP 500"):
            _get_whisper_segments_remote(audio_file, config)

    def test_remote_no_url(self, tmp_path: Path) -> None:
        from stt.diarize import _get_whisper_segments_remote

        audio_file = tmp_path / "test.wav"
        config = WhisperConfig(api_url=None)
        with pytest.raises(DiarizationError, match="requires api_url"):
            _get_whisper_segments_remote(audio_file, config)


class TestRunDiarization:
    """Tests for _run_diarization unwrapping pyannote v4 DiarizeOutput."""

    @patch("stt.diarize.torchaudio.load")
    @patch("stt.diarize.Pipeline.from_pretrained")
    def test_unwraps_diarize_output(
        self, mock_from_pretrained: MagicMock, mock_torchaudio_load: MagicMock
    ) -> None:
        """When pyannote v4 returns DiarizeOutput, extract speaker_diarization."""
        from stt.diarize import _run_diarization

        waveform = MagicMock(name="waveform")
        mock_torchaudio_load.return_value = (waveform, 16000)

        annotation = MagicMock(name="Annotation")
        diarize_output = MagicMock(name="DiarizeOutput")
        diarize_output.speaker_diarization = annotation

        mock_pipeline = MagicMock()
        mock_pipeline.return_value = diarize_output
        mock_from_pretrained.return_value = mock_pipeline

        config = DiarizeConfig(hf_token="fake-token")
        result = _run_diarization(Path("/tmp/test.wav"), config)

        mock_pipeline.assert_called_once_with(
            {"waveform": waveform, "sample_rate": 16000}
        )
        assert result is annotation

    @patch("stt.diarize.torchaudio.load")
    @patch("stt.diarize.Pipeline.from_pretrained")
    def test_returns_annotation_directly(
        self, mock_from_pretrained: MagicMock, mock_torchaudio_load: MagicMock
    ) -> None:
        """When pyannote v3 returns Annotation directly, pass it through."""
        from stt.diarize import _run_diarization

        waveform = MagicMock(name="waveform")
        mock_torchaudio_load.return_value = (waveform, 16000)

        annotation = MagicMock(name="Annotation", spec=[])
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = annotation
        mock_from_pretrained.return_value = mock_pipeline

        config = DiarizeConfig(hf_token="fake-token")
        result = _run_diarization(Path("/tmp/test.wav"), config)

        mock_pipeline.assert_called_once_with(
            {"waveform": waveform, "sample_rate": 16000}
        )
        assert result is annotation
