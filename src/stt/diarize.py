"""Speaker diarization via ML service HTTP API."""

import logging
from dataclasses import dataclass
from pathlib import Path

import requests

from stt.config import MLServiceConfig

logger = logging.getLogger(__name__)


class DiarizationError(Exception):
    """Raised when speaker diarization fails."""


@dataclass(frozen=True)
class DiarizedSegment:
    """A text segment with speaker label and timestamps."""

    speaker: str
    start: float
    end: float
    text: str


def diarize_audio(
    audio_file: str | Path,
    ml_service: MLServiceConfig | None = None,
    model: str = "small",
) -> list[DiarizedSegment]:
    """Transcribe and diarize an audio file via the ML service.

    Args:
        audio_file: Path to the audio file.
        ml_service: ML service configuration.
        model: Whisper model name to use.

    Returns:
        List of DiarizedSegment with speaker labels, timestamps, and text.

    Raises:
        DiarizationError: If diarization fails.
        FileNotFoundError: If the audio file does not exist.
    """
    if ml_service is None:
        ml_service = MLServiceConfig()

    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    url = f"{ml_service.base_url.rstrip('/')}/v1/diarize"

    try:
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/wav")}
            data = {"model": model}
            response = requests.post(
                url, files=files, data=data, timeout=ml_service.timeout
            )

        if response.status_code == 503:
            raise DiarizationError("HF_STT_TOKEN not configured on ML service")

        if response.status_code != 200:
            raise DiarizationError(
                f"ML service diarization failed (HTTP {response.status_code}): "
                f"{response.text}"
            )

        result = response.json()
        segments = [
            DiarizedSegment(
                speaker=s["speaker"],
                start=s["start"],
                end=s["end"],
                text=s["text"],
            )
            for s in result.get("segments", [])
        ]

        logger.info("Diarization complete: %d segments", len(segments))
        return segments
    except DiarizationError:
        raise
    except requests.RequestException as e:
        raise DiarizationError(f"Failed to connect to ML service at {url}: {e}") from e
    except (KeyError, ValueError) as e:
        raise DiarizationError(f"Unexpected response from ML service: {e}") from e


def format_diarized_segments(segments: list[DiarizedSegment]) -> str:
    """Format diarized segments as readable text with speaker labels.

    Consecutive segments from the same speaker are merged under one label.

    Args:
        segments: List of diarized segments.

    Returns:
        Formatted text with speaker labels.
    """
    if not segments:
        return ""

    lines: list[str] = []
    current_speaker: str | None = None
    current_texts: list[str] = []

    for seg in segments:
        if seg.speaker != current_speaker:
            if current_speaker is not None:
                lines.append(f"**{current_speaker}:**\n{' '.join(current_texts)}")
            current_speaker = seg.speaker
            current_texts = [seg.text]
        else:
            current_texts.append(seg.text)

    if current_speaker is not None:
        lines.append(f"**{current_speaker}:**\n{' '.join(current_texts)}")

    return "\n\n".join(lines)
