"""Audio transcription using faster-whisper."""

import logging
from pathlib import Path

from faster_whisper import WhisperModel

from stt.config import WhisperConfig

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""


def transcribe_audio(
    audio_file: str | Path,
    config: WhisperConfig | None = None,
) -> str:
    """Transcribe an audio file to text using faster-whisper.

    Args:
        audio_file: Path to the audio file to transcribe.
        config: Whisper configuration. Uses defaults if None.

    Returns:
        The transcribed text as a single string.

    Raises:
        FileNotFoundError: If the audio file does not exist.
        TranscriptionError: If transcription fails.
    """
    if config is None:
        config = WhisperConfig()

    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info(
        "Starting transcription: file=%s, model=%s, device=%s",
        audio_path,
        config.model_name,
        config.device,
    )

    try:
        model = WhisperModel(config.model_name, device=config.device)
        segments, info = model.transcribe(str(audio_path))

        logger.info(
            "Detected language: %s (probability: %.2f)",
            info.language,
            info.language_probability,
        )

        transcript = " ".join(segment.text for segment in segments)
        logger.info("Transcription complete: %d characters", len(transcript))
        return transcript.strip()

    except Exception as e:
        raise TranscriptionError(f"Failed to transcribe {audio_path}: {e}") from e
