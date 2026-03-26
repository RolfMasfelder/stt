"""Speaker diarization using pyannote.audio combined with whisper transcription."""

import logging
from dataclasses import dataclass
from pathlib import Path

import requests
import torch
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

from stt.config import DiarizeConfig, WhisperConfig

logger = logging.getLogger(__name__)


class DiarizationError(Exception):
    """Raised when speaker diarization fails."""


@dataclass
class DiarizedSegment:
    """A text segment with speaker label and timestamps."""

    speaker: str
    start: float
    end: float
    text: str


def _get_whisper_segments_local(
    audio_path: Path, config: WhisperConfig
) -> list[tuple[float, float, str]]:
    """Get transcription segments with timestamps using local whisper."""
    model = WhisperModel(config.model_name, device=config.device)
    segments, info = model.transcribe(str(audio_path))

    logger.info(
        "Detected language: %s (probability: %.2f)",
        info.language,
        info.language_probability,
    )

    return [(seg.start, seg.end, seg.text.strip()) for seg in segments]


def _get_whisper_segments_remote(
    audio_path: Path, config: WhisperConfig
) -> list[tuple[float, float, str]]:
    """Get transcription segments with timestamps from remote faster-whisper-server."""
    url = config.transcription_url
    if not url:
        raise DiarizationError("Remote transcription requires api_url to be set")

    with open(audio_path, "rb") as f:
        files = {"file": (audio_path.name, f, "audio/wav")}
        data = {
            "model": config.model_name,
            "response_format": "verbose_json",
        }
        response = requests.post(url, files=files, data=data, timeout=config.timeout)

    if response.status_code != 200:
        raise DiarizationError(
            f"Remote transcription failed (HTTP {response.status_code}): "
            f"{response.text}"
        )

    result = response.json()
    segments = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if text:
            segments.append((seg["start"], seg["end"], text))

    return segments


def _run_diarization(audio_path: Path, config: DiarizeConfig):
    """Run pyannote speaker diarization on audio."""
    pipeline = Pipeline.from_pretrained(config.model_name, token=config.hf_token)

    if config.device != "cpu":
        pipeline.to(torch.device(config.device))

    return pipeline(str(audio_path))


def _assign_speaker(start: float, end: float, diarization) -> str:
    """Find the speaker that covers most of a given time range."""
    speakers: dict[str, float] = {}
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        overlap_start = max(start, turn.start)
        overlap_end = min(end, turn.end)
        if overlap_start < overlap_end:
            speakers[speaker] = speakers.get(speaker, 0.0) + (
                overlap_end - overlap_start
            )

    if speakers:
        return max(speakers, key=speakers.get)
    return "UNKNOWN"


def diarize_audio(
    audio_file: str | Path,
    whisper_config: WhisperConfig,
    diarize_config: DiarizeConfig,
) -> list[DiarizedSegment]:
    """Transcribe and diarize an audio file.

    Combines faster-whisper transcription (with timestamps) and pyannote
    speaker diarization to produce speaker-labeled text segments.

    Args:
        audio_file: Path to the audio file.
        whisper_config: Whisper configuration for transcription.
        diarize_config: Diarization configuration (requires hf_token).

    Returns:
        List of DiarizedSegment with speaker labels, timestamps, and text.

    Raises:
        DiarizationError: If diarization fails.
        FileNotFoundError: If the audio file does not exist.
    """
    if not diarize_config.hf_token:
        raise DiarizationError("HuggingFace token required for speaker diarization")

    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        # Step 1: Get transcription segments with timestamps
        logger.info("Step 1/2: Transcribing audio with timestamps...")
        if whisper_config.api_url:
            whisper_segments = _get_whisper_segments_remote(audio_path, whisper_config)
        else:
            whisper_segments = _get_whisper_segments_local(audio_path, whisper_config)
        logger.info("Got %d transcription segments", len(whisper_segments))

        # Step 2: Run speaker diarization
        logger.info("Step 2/2: Running speaker diarization...")
        diarization = _run_diarization(audio_path, diarize_config)

        # Step 3: Merge - assign speaker to each whisper segment
        result = []
        for start, end, text in whisper_segments:
            if text:
                speaker = _assign_speaker(start, end, diarization)
                result.append(
                    DiarizedSegment(speaker=speaker, start=start, end=end, text=text)
                )

        # Normalize speaker names (SPEAKER_00 → Sprecher 1, etc.)
        speaker_map: dict[str, str] = {}
        for seg in result:
            if seg.speaker not in speaker_map:
                speaker_map[seg.speaker] = f"Sprecher {len(speaker_map) + 1}"
            seg.speaker = speaker_map[seg.speaker]

        logger.info(
            "Diarization complete: %d segments, %d speakers",
            len(result),
            len(speaker_map),
        )
        return result
    except DiarizationError:
        raise
    except Exception as e:
        raise DiarizationError(f"Failed to diarize {audio_path}: {e}") from e


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
