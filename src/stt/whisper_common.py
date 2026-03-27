"""Shared utilities for whisper transcription (local and remote)."""

import logging
import subprocess
from pathlib import Path

import requests
from faster_whisper import WhisperModel

from stt.config import WhisperConfig

logger = logging.getLogger(__name__)

_WHISPER_SAMPLE_RATE = 16000
_WHISPER_CHANNELS = 1


def convert_to_whisper_format(audio_path: Path) -> Path:
    """Convert an audio file to the native faster-whisper format (16 kHz, mono, 16-bit PCM WAV).

    Returns the path to the converted file (a temp file next to the original).
    If the input is already in the correct format, returns the original path unchanged.

    Raises:
        RuntimeError: If ffmpeg conversion fails.
    """
    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=sample_rate,channels,codec_name",
        "-of",
        "csv=p=0",
        str(audio_path),
    ]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split(",")
        if len(parts) == 3:
            codec, sample_rate, channels = parts[0], int(parts[1]), int(parts[2])
            if (
                codec == "pcm_s16le"
                and sample_rate == _WHISPER_SAMPLE_RATE
                and channels == _WHISPER_CHANNELS
            ):
                logger.info(
                    "Audio already in whisper-native format, skipping conversion"
                )
                return audio_path
    except (subprocess.CalledProcessError, ValueError):
        pass  # proceed with conversion

    converted_path = audio_path.with_suffix(".whisper.wav")
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(audio_path),
        "-ar",
        str(_WHISPER_SAMPLE_RATE),
        "-ac",
        str(_WHISPER_CHANNELS),
        "-c:a",
        "pcm_s16le",
        str(converted_path),
    ]
    logger.info(
        "Converting %s to whisper-native format (16kHz, mono, 16-bit PCM)",
        audio_path.name,
    )

    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg conversion failed: {e.stderr}") from e

    original_mb = audio_path.stat().st_size / (1024 * 1024)
    converted_mb = converted_path.stat().st_size / (1024 * 1024)
    logger.info("Converted: %.1f MB → %.1f MB", original_mb, converted_mb)
    return converted_path


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
