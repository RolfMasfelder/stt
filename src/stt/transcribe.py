"""Audio transcription using faster-whisper (local or remote)."""

import logging
from pathlib import Path

import requests

from stt.config import WhisperConfig
from stt.whisper_common import post_whisper_remote, run_whisper_local

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""


def _transcribe_local(audio_path: Path, config: WhisperConfig) -> str:
    """Run transcription locally with faster-whisper."""
    logger.info(
        "Starting local transcription: file=%s, model=%s, device=%s",
        audio_path,
        config.model_name,
        config.device,
    )

    segments, _info = run_whisper_local(audio_path, config)
    transcript = " ".join(segment.text for segment in segments)
    logger.info("Transcription complete: %d characters", len(transcript))
    return transcript.strip()


def _transcribe_remote(audio_path: Path, config: WhisperConfig) -> str:
    """Send audio to a remote faster-whisper-server for transcription."""
    logger.info(
        "Starting remote transcription: file=%s, url=%s, model=%s",
        audio_path,
        config.transcription_url,
        config.model_name,
    )

    try:
        response = post_whisper_remote(audio_path, config, response_format="text")
    except ValueError as e:
        raise TranscriptionError(str(e)) from e

    if response.status_code != 200:
        raise TranscriptionError(
            f"Remote transcription failed (HTTP {response.status_code}): "
            f"{response.text}"
        )

    transcript = response.text.strip()
    logger.info("Remote transcription complete: %d characters", len(transcript))
    return transcript


def transcribe_audio(
    audio_file: str | Path,
    config: WhisperConfig | None = None,
) -> str:
    """Transcribe an audio file to text.

    When ``config.api_url`` is set the audio is sent to a remote
    faster-whisper-server instance; otherwise transcription runs locally.

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

    try:
        if config.api_url:
            return _transcribe_remote(audio_path, config)
        return _transcribe_local(audio_path, config)
    except TranscriptionError:
        raise
    except (RuntimeError, OSError, requests.RequestException) as e:
        raise TranscriptionError(f"Failed to transcribe {audio_path}: {e}") from e
