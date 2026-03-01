"""Text summarization via LM Studio API."""

import logging

import requests

from stt.config import LMStudioConfig

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "Fasse Texte zusammen."

STRUCTURE_SYSTEM_PROMPT = (
    "Du bist ein Textanalyst. Analysiere das folgende Transkript und "
    "gliedere es in thematische Abschnitte. Gib jedem Abschnitt eine "
    "aussagekräftige Überschrift und den zugehörigen Text. "
    "Formatiere die Ausgabe als Markdown mit ## Überschriften."
)

SUMMARY_SYSTEM_PROMPT = (
    "Du bist ein Zusammenfassungs-Experte. Erstelle eine prägnante "
    "Zusammenfassung des folgenden strukturierten Textes. "
    "Behalte die thematische Gliederung bei und fasse jeden Abschnitt "
    "in wenigen Sätzen zusammen. Formatiere die Ausgabe als Markdown."
)


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
            timeout=config.timeout,
        )
        response.raise_for_status()
    except requests.ConnectionError as e:
        raise SummarizationError(
            f"Cannot connect to LM Studio at {config.url}: {e}"
        ) from e
    except requests.Timeout as e:
        raise SummarizationError(
            f"Request to LM Studio timed out after {config.timeout}s: {e}"
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


def structure_text(
    text: str,
    config: LMStudioConfig | None = None,
) -> str:
    """Structure a transcript into thematic sections.

    Args:
        text: The raw transcript text to structure.
        config: LM Studio configuration. Uses defaults if None.

    Returns:
        The structured text with thematic sections as Markdown.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If the API request fails.
    """
    logger.info("Structuring transcript (%d characters)", len(text))
    return summarize_text(text, config, system_prompt=STRUCTURE_SYSTEM_PROMPT)


def process_transcript(
    text: str,
    config: LMStudioConfig | None = None,
) -> tuple[str, str]:
    """Full pipeline: structure a transcript, then summarize it.

    Performs two LLM calls:
    1. Structure the raw transcript into thematic sections.
    2. Summarize the structured text.

    Args:
        text: The raw transcript text.
        config: LM Studio configuration. Uses defaults if None.

    Returns:
        A tuple of (structured_text, summary).

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If any API request fails.
    """
    structured = structure_text(text, config)
    logger.info("Summarizing structured text (%d characters)", len(structured))
    summary = summarize_text(structured, config, system_prompt=SUMMARY_SYSTEM_PROMPT)
    return structured, summary
