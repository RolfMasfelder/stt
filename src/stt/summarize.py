"""Text summarization via LM Studio API."""

import logging
import re

import requests

from stt.config import LMStudioConfig

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "Fasse Texte zusammen."

STRUCTURE_SYSTEM_PROMPT = (
    "Du erhältst ein Transkript einer Audio-Aufnahme. "
    "Gliedere den VOLLSTÄNDIGEN Inhalt in thematische Abschnitte. "
    "Gib jedem Abschnitt eine kurze, aussagekräftige Überschrift (## Markdown). "
    "Antworte ausschließlich mit dem gegliederten Text. "
    "Keine Erklärungen, keine Analyse, kein Kommentar."
)

SUMMARY_SYSTEM_PROMPT = (
    "Du erhältst einen bereits in Abschnitte gegliederten Text im markdown Format. "
    "Jeder Abschnitt wird mit einem ## Überschrift markiert. "
    "Erstelle eine KURZE Zusammenfassung: maximal 2-3 Sätze pro Abschnitt. "
    "Ziel ist eine kompakte Übersicht, NICHT eine Wiederholung des vollen Textes. "
    "Behalte die Überschriften bei, aber kürze den Inhalt radikal auf das Wesentliche. "
    "Antworte ausschließlich mit der Zusammenfassung im Markdown-Format."
)

DIARIZE_SYSTEM_PROMPT = (
    "Du erhältst ein Transkript einer Audio-Aufnahme mit mehreren Sprechern. "
    "Kennzeichne jeden Sprecherwechsel mit einem Speaker-Label "
    "(z.B. **Sprecher 1:**, **Sprecher 2:**, etc.). "
    "Erkenne Sprecherwechsel anhand von Kontextwechseln, Anreden, "
    "Fragen und Antworten, unterschiedlichem Sprachstil oder Themenwechseln. "
    "Wenn der gleiche Sprecher mehrere Sätze hintereinander sagt, "
    "fasse sie unter einem Label zusammen. "
    "Antworte ausschließlich mit dem zugeordneten Text. "
    "Keine Erklärungen, keine Analyse."
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
        content = result["choices"][0]["message"]["content"]
        # Strip model thinking blocks (e.g. <think>...</think>)
        summary = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
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


def diarize_text(
    text: str,
    config: LMStudioConfig | None = None,
) -> str:
    """Add speaker labels to a transcript using LLM heuristics.

    Analyzes context switches, questions/answers, speaking styles and
    topic changes to assign speaker labels (Sprecher 1, Sprecher 2, etc.).

    Args:
        text: The raw transcript text.
        config: LM Studio configuration. Uses defaults if None.

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
    config: LMStudioConfig | None = None,
    diarize: bool = False,
) -> tuple[str, str, str | None]:
    """Full pipeline: optionally diarize, structure, then summarize.

    Performs 2-3 LLM calls:
    1. (Optional) Assign speaker labels to the transcript.
    2. Structure the transcript into thematic sections.
    3. Summarize the structured text.

    Args:
        text: The raw transcript text.
        config: LM Studio configuration. Uses defaults if None.
        diarize: If True, run speaker diarization before structuring.

    Returns:
        A tuple of (structured_text, summary, diarized_text).
        diarized_text is None when diarize=False.

    Raises:
        ValueError: If the input text is empty.
        SummarizationError: If any API request fails.
    """
    diarized: str | None = None
    input_text = text

    if diarize:
        diarized = diarize_text(text, config)
        input_text = diarized

    structured = structure_text(input_text, config)
    logger.info("Summarizing structured text (%d characters)", len(structured))
    summary = summarize_text(structured, config, system_prompt=SUMMARY_SYSTEM_PROMPT)
    return structured, summary, diarized
