"""Tests for the summarization module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from stt.config import LMStudioConfig
from stt.summarize import SummarizationError, summarize_text


class TestSummarizeText:
    """Tests for summarize_text."""

    def test_empty_text_raises(self) -> None:
        """Should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="must not be empty"):
            summarize_text("")

    def test_whitespace_only_raises(self) -> None:
        """Should raise ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match="must not be empty"):
            summarize_text("   \n\t  ")

    @patch("stt.summarize.requests.post")
    def test_successful_summarization(self, mock_post: MagicMock) -> None:
        """Should return summary from LM Studio response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Zusammenfassung"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = summarize_text("Ein langer Text zum Zusammenfassen.")
        assert result == "Zusammenfassung"

    @patch("stt.summarize.requests.post")
    def test_connection_error(self, mock_post: MagicMock) -> None:
        """Should wrap ConnectionError in SummarizationError."""
        mock_post.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(SummarizationError, match="Cannot connect"):
            summarize_text("Test text")

    @patch("stt.summarize.requests.post")
    def test_timeout_error(self, mock_post: MagicMock) -> None:
        """Should wrap Timeout in SummarizationError."""
        mock_post.side_effect = requests.Timeout("Timed out")

        with pytest.raises(SummarizationError, match="timed out"):
            summarize_text("Test text")

    @patch("stt.summarize.requests.post")
    def test_http_error(self, mock_post: MagicMock) -> None:
        """Should wrap HTTPError in SummarizationError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            response=mock_response
        )
        mock_post.return_value = mock_response

        with pytest.raises(SummarizationError, match="HTTP 500"):
            summarize_text("Test text")

    @patch("stt.summarize.requests.post")
    def test_malformed_response(self, mock_post: MagicMock) -> None:
        """Should wrap KeyError from bad JSON in SummarizationError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "format"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with pytest.raises(SummarizationError, match="Unexpected response format"):
            summarize_text("Test text")

    @patch("stt.summarize.requests.post")
    def test_uses_config(self, mock_post: MagicMock) -> None:
        """Should send request to configured URL with correct model."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Summary"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        config = LMStudioConfig(host="myhost", port=9999, model="my-model")
        summarize_text("Test text", config)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args.args[0] == "http://myhost:9999/v1/chat/completions"
        assert call_args.kwargs["json"]["model"] == "my-model"

    @patch("stt.summarize.requests.post")
    def test_custom_system_prompt(self, mock_post: MagicMock) -> None:
        """Should use the provided system prompt."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Result"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        summarize_text("Text", system_prompt="Custom prompt")

        call_args = mock_post.call_args
        messages = call_args.kwargs["json"]["messages"]
        assert messages[0]["content"] == "Custom prompt"
