"""Tests for the STT client."""

from unittest.mock import MagicMock, patch

import pytest

from stt.client import ClientError, DiarizedResult, ProcessResult, STTClient

# All tests that use _post_file need convert_to_whisper_format to be a no-op
_PATCH_CONVERT = patch("stt.client.convert_to_whisper_format", side_effect=lambda p: p)


class TestSTTClientHealth:
    """Tests for the health check method."""

    @patch("stt.client.requests.get")
    def test_health_ok(self, mock_get) -> None:
        mock_get.return_value = MagicMock(status_code=200)
        client = STTClient("http://localhost:8001")
        assert client.health() is True

    @patch("stt.client.requests.get")
    def test_health_fail(self, mock_get) -> None:
        mock_get.return_value = MagicMock(status_code=500)
        client = STTClient("http://localhost:8001")
        assert client.health() is False

    @patch("stt.client.requests.get")
    def test_health_connection_error(self, mock_get) -> None:
        import requests

        mock_get.side_effect = requests.ConnectionError("refused")
        client = STTClient("http://localhost:8001")
        assert client.health() is False


class TestSTTClientTranscribe:
    """Tests for the transcribe method."""

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_transcribe_success(self, mock_post, _mock_convert, tmp_path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake audio")

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"text": "Hello World"}
        mock_post.return_value = mock_resp

        client = STTClient("http://localhost:8001")
        result = client.transcribe(audio)
        assert result == "Hello World"
        mock_post.assert_called_once()

    def test_transcribe_file_not_found(self, tmp_path) -> None:
        client = STTClient("http://localhost:8001")
        with pytest.raises(FileNotFoundError):
            client.transcribe(tmp_path / "missing.wav")

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_transcribe_server_error(self, mock_post, _mock_convert, tmp_path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        mock_resp = MagicMock(status_code=500, text="Internal Server Error")
        mock_post.return_value = mock_resp

        client = STTClient("http://localhost:8001")
        with pytest.raises(ClientError, match="HTTP 500"):
            client.transcribe(audio)

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_transcribe_connection_error(
        self, mock_post, _mock_convert, tmp_path
    ) -> None:
        import requests

        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        mock_post.side_effect = requests.ConnectionError("refused")
        client = STTClient("http://localhost:8001")
        with pytest.raises(ClientError, match="failed"):
            client.transcribe(audio)


class TestSTTClientDiarize:
    """Tests for the diarize method."""

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_diarize_success(self, mock_post, _mock_convert, tmp_path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "text": "Hallo Hi",
            "diarized_text": "**Sprecher 1:**\nHallo\n\n**Sprecher 2:**\nHi",
            "segments": [
                {"speaker": "Sprecher 1", "start": 0.0, "end": 1.5, "text": "Hallo"},
                {"speaker": "Sprecher 2", "start": 1.5, "end": 3.0, "text": "Hi"},
            ],
        }
        mock_post.return_value = mock_resp

        client = STTClient("http://localhost:8001")
        result = client.diarize(audio)
        assert isinstance(result, DiarizedResult)
        assert result.text == "Hallo Hi"
        assert len(result.segments) == 2

    def test_diarize_file_not_found(self, tmp_path) -> None:
        client = STTClient("http://localhost:8001")
        with pytest.raises(FileNotFoundError):
            client.diarize(tmp_path / "missing.wav")


class TestSTTClientProcess:
    """Tests for the process method."""

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_process_success(self, mock_post, _mock_convert, tmp_path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "text": "Transkript",
            "diarized_text": "**Sprecher 1:**\nTranskript",
            "structured_text": "## Struktur",
            "summary": "Zusammenfassung",
        }
        mock_post.return_value = mock_resp

        client = STTClient("http://localhost:8001")
        result = client.process(audio, diarize=True)
        assert isinstance(result, ProcessResult)
        assert result.text == "Transkript"
        assert result.structured_text == "## Struktur"
        assert result.summary == "Zusammenfassung"
        assert result.diarized_text is not None

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_process_without_diarize(self, mock_post, _mock_convert, tmp_path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {
            "text": "Transkript",
            "diarized_text": None,
            "structured_text": "## Struktur",
            "summary": "Zusammenfassung",
        }
        mock_post.return_value = mock_resp

        client = STTClient("http://localhost:8001")
        result = client.process(audio, diarize=False)
        assert result.diarized_text is None

    def test_process_file_not_found(self, tmp_path) -> None:
        client = STTClient("http://localhost:8001")
        with pytest.raises(FileNotFoundError):
            client.process(tmp_path / "missing.wav")

    @_PATCH_CONVERT
    @patch("stt.client.requests.post")
    def test_process_server_error(self, mock_post, _mock_convert, tmp_path) -> None:
        audio = tmp_path / "test.wav"
        audio.write_bytes(b"fake")

        mock_resp = MagicMock(status_code=500, text="Error")
        mock_post.return_value = mock_resp

        client = STTClient("http://localhost:8001")
        with pytest.raises(ClientError, match="HTTP 500"):
            client.process(audio)


class TestSTTClientBaseURL:
    """Tests for URL handling."""

    def test_trailing_slash_stripped(self) -> None:
        client = STTClient("http://localhost:8001/")
        assert client.base_url == "http://localhost:8001"

    def test_custom_timeout(self) -> None:
        client = STTClient("http://localhost:8001", timeout=300)
        assert client.timeout == 300
