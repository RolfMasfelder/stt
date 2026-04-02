"""Text summarization via LM Studio API."""

import logging
import re
from dataclasses import dataclass

import requests

from stt.config import LLMConfig
from stt.prompts import (
    DEFAULT_SYSTEM_PROMPT,
    DIARIZE_SYSTEM_PROMPT,
    STRUCTURE_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessResult:
    """Result from the full processing pipeline."""

    structured_text: str
    summary: str
    diarized_text: str | None


class SummarizationError(Exception):
    """Raised when summarization via LLM fails."""


def summarize_text(
    text: str,
    config: LLMConfig | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> str:
    """Summarize text using an LLM.

    Args:
        text: The text to summarize.
        config: LLM configuration. Uses defaults if None.
        system_prompt: System prompt for the LLM.

    Returns:
        The summarized text.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    if config is None:
        config = LLMConfig()

    if not text.strip():
        raise ValueError("Input text must not be empty")

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    }

    logger.info("Sending summarization request to %s", config.url)
    logger.debug("System prompt: %s", system_prompt[:80])
    logger.debug("Payload: model=%s, text_length=%d", config.model, len(text))

    try:
        response = requests.post(
            config.url,
            json=payload,
            timeout=config.timeout,
        )
        response.raise_for_status()
    except requests.ConnectionError as e:
        raise SummarizationError(f"Cannot connect to LLM at {config.url}: {e}") from e
    except requests.Timeout as e:
        raise SummarizationError(
            f"Request to LLM timed out after {config.timeout}s: {e}"
        ) from e
    except requests.HTTPError as e:
        raise SummarizationError(
            f"LLM returned HTTP {response.status_code}: {response.text}"
        ) from e

    try:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        # Strip model thinking blocks (e.g. <think>...</think>)
        summary = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    except (KeyError, IndexError, ValueError) as e:
        raise SummarizationError(f"Unexpected response format from LLM: {e}") from e

    logger.info("Summarization complete: %d characters", len(summary))
    return summary


def structure_text(
    text: str,
    config: LLMConfig | None = None,
) -> str:
    """Structure a transcript into thematic sections.

    Args:
        text: The raw transcript text to structure.
        config: LLM configuration. Uses defaults if None.

    Returns:
        The structured text with thematic sections as Markdown.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    logger.info("Structuring transcript (%d characters)", len(text))
    return summarize_text(text, config, system_prompt=STRUCTURE_SYSTEM_PROMPT)


def diarize_text(
    text: str,
    config: LLMConfig | None = None,
) -> str:
    """Add speaker labels to a transcript using LLM heuristics.

    Analyzes context switches, questions/answers, speaking styles and
    topic changes to assign speaker labels (Sprecher 1, Sprecher 2, etc.).

    Args:
        text: The raw transcript text.
        config: LLM configuration. Uses defaults if None.

    Returns:
        The transcript with speaker labels added.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    logger.info("Diarizing transcript (%d characters)", len(text))
    return summarize_text(text, config, system_prompt=DIARIZE_SYSTEM_PROMPT)


def process_transcript(
    text: str,
    config: LLMConfig | None = None,
    diarize: bool = False,
    diarized_text: str | None = None,
) -> ProcessResult:
    """Full pipeline: optionally diarize, structure, then summarize.

    Performs 2-3 LLM calls:
    1. (Optional) Assign speaker labels to the transcript.
    2. Structure the transcript into thematic sections.
    3. Summarize the structured text.

    Args:
        text: The raw transcript text.
        config: LLM configuration. Uses defaults if None.
        diarize: If True, run speaker diarization before structuring.
        diarized_text: Pre-computed diarized text (e.g. from audio-based
            diarization). When set, skips LLM-based diarization.

    Returns:
        ProcessResult with structured_text, summary, and optional diarized_text.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If any API request fails.
    """
    diarized = diarized_text
    input_text = text

    if diarize:
        diarized = diarize_text(text, config)
        input_text = diarized

    structured = structure_text(input_text, config)
    logger.info("Summarizing structured text (%d characters)", len(structured))
    summary = summarize_text(structured, config, system_prompt=SUMMARY_SYSTEM_PROMPT)
    return ProcessResult(
        structured_text=structured, summary=summary, diarized_text=diarized
    )
