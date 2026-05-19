"""Text summarization via Ollama API (OpenAI-compatible)."""

import logging
import re
import time
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

_RETRY_STATUS_CODES = {429, 503}

_LANGUAGE_NAMES: dict[str, str] = {
    "en": "Englisch",
    "fr": "Französisch",
    "es": "Spanisch",
    "it": "Italienisch",
    "pt": "Portugiesisch",
    "nl": "Niederländisch",
    "pl": "Polnisch",
    "ru": "Russisch",
    "tr": "Türkisch",
    "ar": "Arabisch",
    "zh": "Chinesisch",
    "ja": "Japanisch",
    "ko": "Koreanisch",
}


def _language_suffix(language: str) -> str:
    """Return a language instruction for non-German/non-auto languages."""
    if language in ("auto", "de", ""):
        return ""
    lang_name = _LANGUAGE_NAMES.get(language, language.upper())
    return f"\nAntworte ausschließlich auf {lang_name}."


_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # seconds; delay = base * attempt


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
    language: str = "auto",
) -> str:
    """Summarize text using an LLM.

    Args:
        text: The text to summarize.
        config: LLM configuration. Uses defaults if None.
        system_prompt: System prompt for the LLM.
        language: Language code for the output (e.g. 'de', 'fr') or 'auto'.

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

    suffix = _language_suffix(language)
    effective_prompt = system_prompt + suffix if suffix else system_prompt

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": effective_prompt},
            {"role": "user", "content": text},
        ],
    }

    logger.info("Sending summarization request to %s", config.url)
    logger.debug("System prompt: %s", system_prompt[:80])
    logger.debug("Payload: model=%s, text_length=%d", config.model, len(text))

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.post(
                config.url,
                json=payload,
                timeout=config.timeout,
            )
            if response.status_code in _RETRY_STATUS_CODES and attempt < _MAX_RETRIES:
                delay = _RETRY_BACKOFF_BASE * attempt
                logger.warning(
                    "LLM returned HTTP %d (attempt %d/%d), retrying in %.0fs...",
                    response.status_code,
                    attempt,
                    _MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            break
        except requests.ConnectionError as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BACKOFF_BASE * attempt
                logger.warning(
                    "Cannot connect to LLM (attempt %d/%d), retrying in %.0fs...",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
            else:
                raise SummarizationError(
                    f"Cannot connect to LLM at {config.url}: {e}"
                ) from e
        except requests.Timeout as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BACKOFF_BASE * attempt
                logger.warning(
                    "LLM request timed out (attempt %d/%d), retrying in %.0fs...",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                )
                time.sleep(delay)
            else:
                raise SummarizationError(
                    f"Request to LLM timed out after {config.timeout}s: {e}"
                ) from e
        except requests.HTTPError as e:
            raise SummarizationError(
                f"LLM returned HTTP {response.status_code}: {response.text}"
            ) from e
    else:
        raise SummarizationError(
            f"LLM unavailable after {_MAX_RETRIES} attempts: {last_error}"
        )

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
    language: str = "auto",
) -> str:
    """Structure a transcript into thematic sections.

    Args:
        text: The raw transcript text to structure.
        config: LLM configuration. Uses defaults if None.
        language: Language code for the output or 'auto'.

    Returns:
        The structured text with thematic sections as Markdown.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    logger.info("Structuring transcript (%d characters)", len(text))
    return summarize_text(
        text, config, system_prompt=STRUCTURE_SYSTEM_PROMPT, language=language
    )


def diarize_text(
    text: str,
    config: LLMConfig | None = None,
    language: str = "auto",
) -> str:
    """Add speaker labels to a transcript using LLM heuristics.

    Analyzes context switches, questions/answers, speaking styles and
    topic changes to assign speaker labels (Sprecher 1, Sprecher 2, etc.).

    Args:
        text: The raw transcript text.
        config: LLM configuration. Uses defaults if None.
        language: Language code for the output or 'auto'.

    Returns:
        The transcript with speaker labels added.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    logger.info("Diarizing transcript (%d characters)", len(text))
    return summarize_text(
        text, config, system_prompt=DIARIZE_SYSTEM_PROMPT, language=language
    )


def process_transcript(
    text: str,
    config: LLMConfig | None = None,
    diarize: bool = False,
    diarized_text: str | None = None,
    language: str = "auto",
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
        language: Language code for LLM output (e.g. 'de', 'fr') or 'auto'.

    Returns:
        ProcessResult with structured_text, summary, and optional diarized_text.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If any API request fails.
    """
    diarized = diarized_text
    input_text = text

    if diarize:
        diarized = diarize_text(text, config, language=language)
        input_text = diarized

    structured = structure_text(input_text, config, language=language)
    logger.info("Summarizing structured text (%d characters)", len(structured))
    summary = summarize_text(
        structured, config, system_prompt=SUMMARY_SYSTEM_PROMPT, language=language
    )
    return ProcessResult(
        structured_text=structured, summary=summary, diarized_text=diarized
    )
