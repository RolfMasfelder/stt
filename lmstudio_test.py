"""Test script for LM Studio API connectivity and summarization.

Use 'python -m stt <audio_file> --summarize' for production use.
"""

from stt.config import load_config
from stt.logging_setup import setup_logging
from stt.summarize import SummarizationError, summarize_text

if __name__ == "__main__":
    config = load_config()
    setup_logging(config.log_level)

    print(f"Connecting to LM Studio at {config.lm_studio.url}")
    print(f"Using model: {config.lm_studio.model}")

    # Example transcript for testing
    transcript = "Das ist ein Test-Transkript für die Zusammenfassung."

    try:
        summary = summarize_text(transcript, config.lm_studio)
        print(f"\nErgebnis:\n{summary}")
    except SummarizationError as e:
        print(f"\nFehler: {e}")
