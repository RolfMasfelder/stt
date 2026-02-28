"""Text summarization via LM Studio API."""

import logging

import requests

from stt.config import LMStudioConfig

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "Fasse Texte zusammen."
REQUEST_TIMEOUT_SECONDS = 120


class SummarizationError(Exception):
    """Raised when summarization via LM Studio fails."""


def summarize_text(
    text: str,
    config: LMStudioConfig | None = None,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> str:
    """Summarize text using an LM Studio model.

    Args:
        text: The text to summarize.
        config: LM Studio configuration. Uses defaults if None.
        system_prompt: System prompt for the LLM.

    Returns:
        The summarized text.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    if config is None:
        config = LMStudioConfig()

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
    logger.debug("Payload: model=%s, text_length=%d", config.model, len(text))

    try:
        response = requests.post(
            config.url,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.ConnectionError as e:
        raise SummarizationError(
            f"Cannot connect to LM Studio at {config.url}: {e}"
        ) from e
    except requests.Timeout as e:
        raise SummarizationError(
            f"Request to LM Studio timed out after {REQUEST_TIMEOUT_SECONDS}s: {e}"
        ) from e
    except requests.HTTPError as e:
        raise SummarizationError(
            f"LM Studio returned HTTP {response.status_code}: {response.text}"
        ) from e

    try:
        result = response.json()
        summary = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise SummarizationError(
            f"Unexpected response format from LM Studio: {e}"
        ) from e

    logger.info("Summarization complete: %d characters", len(summary))
    return summary
