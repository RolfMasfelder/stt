"""Shared utilities for whisper transcription (local and remote)."""

import logging
from pathlib import Path

import requests
from faster_whisper import WhisperModel

from stt.config import WhisperConfig

logger = logging.getLogger(__name__)


def run_whisper_local(audio_path: Path, config: WhisperConfig):
    """Create WhisperModel, transcribe audio, and log detected language.

    Returns:
        Tuple of (segments_iterator, transcription_info).
    """
    model = WhisperModel(config.model_name, device=config.device)
    segments, info = model.transcribe(str(audio_path))
    logger.info(
        "Detected language: %s (probability: %.2f)",
        info.language,
        info.language_probability,
    )
    return segments, info


def post_whisper_remote(
    audio_path: Path,
    config: WhisperConfig,
    response_format: str = "text",
) -> requests.Response:
    """Post audio to remote whisper API and return the response.

    Raises:
        ValueError: If config.api_url is not set.
    """
    url = config.transcription_url
    if not url:
        raise ValueError("Remote transcription requires api_url to be set")

    with open(audio_path, "rb") as f:
        files = {"file": (audio_path.name, f, "audio/wav")}
        data = {"model": config.model_name, "response_format": response_format}
        return requests.post(url, files=files, data=data, timeout=config.timeout)
