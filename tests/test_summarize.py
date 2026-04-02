"""Tests for the summarization module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from stt.config import LLMConfig
from stt.prompts import (
    DIARIZE_SYSTEM_PROMPT,
    STRUCTURE_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
)
from stt.summarize import (
    SummarizationError,
    diarize_text,
    process_transcript,
    structure_text,
    summarize_text,
)


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
    def test_strips_think_tags(self, mock_post: MagicMock) -> None:
        """Should remove <think>...</think> blocks from model output."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "<think>\nI need to analyze this...\n"
                            "Let me think step by step.\n</think>\n"
                            "## Ergebnis\nDas ist die Antwort."
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = summarize_text("Ein Text.")
        assert "<think>" not in result
        assert "## Ergebnis" in result
        assert result == "## Ergebnis\nDas ist die Antwort."

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

        config = LLMConfig(base_url="http://myhost:9999", model="my-model")
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


class TestStructureText:
    """Tests for structure_text."""

    @patch("stt.summarize.requests.post")
    def test_uses_structure_prompt(self, mock_post: MagicMock) -> None:
        """Should use the STRUCTURE_SYSTEM_PROMPT."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "## Thema 1\nInhalt"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = structure_text("Ein langer Transkript-Text.")

        call_args = mock_post.call_args
        messages = call_args.kwargs["json"]["messages"]
        assert messages[0]["content"] == STRUCTURE_SYSTEM_PROMPT
        assert "## Thema 1" in result

    def test_empty_text_raises(self) -> None:
        """Should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="must not be empty"):
            structure_text("")

    @patch("stt.summarize.requests.post")
    def test_connection_error(self, mock_post: MagicMock) -> None:
        """Should propagate SummarizationError."""
        mock_post.side_effect = requests.ConnectionError("refused")
        with pytest.raises(SummarizationError):
            structure_text("Text")


class TestProcessTranscript:
    """Tests for process_transcript (full pipeline)."""

    @patch("stt.summarize.requests.post")
    def test_two_step_pipeline(self, mock_post: MagicMock) -> None:
        """Should call LM Studio twice: structure then summarize."""
        structured_response = MagicMock()
        structured_response.status_code = 200
        structured_response.json.return_value = {
            "choices": [{"message": {"content": "## Abschnitt 1\nDetails"}}]
        }
        structured_response.raise_for_status = MagicMock()

        summary_response = MagicMock()
        summary_response.status_code = 200
        summary_response.json.return_value = {
            "choices": [{"message": {"content": "Kurze Zusammenfassung"}}]
        }
        summary_response.raise_for_status = MagicMock()

        mock_post.side_effect = [structured_response, summary_response]

        result = process_transcript("Langer Transkript-Text")

        assert mock_post.call_count == 2
        assert "## Abschnitt 1" in result.structured_text
        assert result.summary == "Kurze Zusammenfassung"
        assert result.diarized_text is None

        # First call should use structure prompt
        first_call = mock_post.call_args_list[0]
        assert (
            first_call.kwargs["json"]["messages"][0]["content"]
            == STRUCTURE_SYSTEM_PROMPT
        )

        # Second call should use summary prompt
        second_call = mock_post.call_args_list[1]
        assert (
            second_call.kwargs["json"]["messages"][0]["content"]
            == SUMMARY_SYSTEM_PROMPT
        )

    @patch("stt.summarize.requests.post")
    def test_structure_failure_stops_pipeline(self, mock_post: MagicMock) -> None:
        """Should not attempt summarization if structuring fails."""
        mock_post.side_effect = requests.ConnectionError("refused")

        with pytest.raises(SummarizationError):
            process_transcript("Text")

        assert mock_post.call_count == 1

    def test_empty_text_raises(self) -> None:
        """Should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="must not be empty"):
            process_transcript("")

    @patch("stt.summarize.requests.post")
    def test_three_step_pipeline_with_diarize(self, mock_post: MagicMock) -> None:
        """Should call LM Studio three times when diarize=True."""
        diarize_response = MagicMock()
        diarize_response.status_code = 200
        diarize_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            "**Sprecher 1:** Hallo zusammen.\n"
                            "**Sprecher 2:** Hi, danke f\u00fcr die Einladung."
                        )
                    }
                }
            ]
        }
        diarize_response.raise_for_status = MagicMock()

        structured_response = MagicMock()
        structured_response.status_code = 200
        structured_response.json.return_value = {
            "choices": [{"message": {"content": "## Begr\u00fc\u00dfung\nHallo"}}]
        }
        structured_response.raise_for_status = MagicMock()

        summary_response = MagicMock()
        summary_response.status_code = 200
        summary_response.json.return_value = {
            "choices": [{"message": {"content": "Kurze Zusammenfassung"}}]
        }
        summary_response.raise_for_status = MagicMock()

        mock_post.side_effect = [
            diarize_response,
            structured_response,
            summary_response,
        ]

        result = process_transcript("Hallo zusammen. Hi, danke.", diarize=True)

        assert mock_post.call_count == 3
        assert result.diarized_text is not None
        assert "Sprecher 1" in result.diarized_text
        assert "Sprecher 2" in result.diarized_text

        # First call should use diarize prompt
        first_call = mock_post.call_args_list[0]
        assert (
            first_call.kwargs["json"]["messages"][0]["content"] == DIARIZE_SYSTEM_PROMPT
        )


class TestDiarizeText:
    """Tests for diarize_text."""

    @patch("stt.summarize.requests.post")
    def test_uses_diarize_prompt(self, mock_post: MagicMock) -> None:
        """Should use the DIARIZE_SYSTEM_PROMPT."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "**Sprecher 1:** Hallo\n**Sprecher 2:** Hi"}}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = diarize_text("Hallo. Hi.")

        call_args = mock_post.call_args
        messages = call_args.kwargs["json"]["messages"]
        assert messages[0]["content"] == DIARIZE_SYSTEM_PROMPT
        assert "Sprecher 1" in result

    def test_empty_text_raises(self) -> None:
        """Should raise ValueError for empty text."""
        with pytest.raises(ValueError, match="must not be empty"):
            diarize_text("")

    @patch("stt.summarize.requests.post")
    def test_connection_error(self, mock_post: MagicMock) -> None:
        """Should propagate SummarizationError."""
        mock_post.side_effect = requests.ConnectionError("refused")
        with pytest.raises(SummarizationError):
            diarize_text("Text")


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    @patch("stt.summarize.requests.post")
    def test_json_decode_error(self, mock_post: MagicMock) -> None:
        """Should wrap JSON parse errors in SummarizationError."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        with pytest.raises(SummarizationError, match="Unexpected response format"):
            summarize_text("Test text")

    @patch("stt.summarize.requests.post")
    def test_empty_choices_array(self, mock_post: MagicMock) -> None:
        """Should raise SummarizationError for empty choices."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_post.return_value = mock_response

        with pytest.raises(SummarizationError, match="Unexpected response format"):
            summarize_text("Test text")
