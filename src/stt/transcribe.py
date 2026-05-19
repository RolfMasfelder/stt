"""Audio transcription via ML service HTTP API."""

import logging
from pathlib import Path

import requests

from stt.config import MLServiceConfig

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Raised when audio transcription fails."""


def transcribe_audio(
    audio_file: str | Path,
    ml_service: MLServiceConfig | None = None,
    model: str = "small",
    language: str = "auto",
) -> str:
    """Transcribe an audio file to text via the ML service.

    Args:
        audio_file: Path to the audio file to transcribe.
        ml_service: ML service configuration. Uses defaults if None.
        model: Whisper model name to use.
        language: Language code (e.g. 'de', 'en') or 'auto' for detection.

    Returns:
        The transcribed text as a single string.

    Raises:
        FileNotFoundError: If the audio file does not exist.
        TranscriptionError: If transcription fails.
    """
    if ml_service is None:
        ml_service = MLServiceConfig()

    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    url = f"{ml_service.base_url.rstrip('/')}/v1/transcribe"

    try:
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/wav")}
            data = {"model": model, "language": language}
            response = requests.post(
                url, files=files, data=data, timeout=ml_service.timeout
            )

        if response.status_code != 200:
            raise TranscriptionError(
                f"ML service transcription failed (HTTP {response.status_code}): "
                f"{response.text}"
            )

        result = response.json()
        return result.get("text", "").strip()
    except TranscriptionError:
        raise
    except requests.RequestException as e:
        raise TranscriptionError(
            f"Failed to connect to ML service at {url}: {e}"
        ) from e
    except (KeyError, ValueError) as e:
        raise TranscriptionError(f"Unexpected response from ML service: {e}") from e
