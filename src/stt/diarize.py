"""Speaker diarization using pyannote.audio combined with whisper transcription."""

import logging
from dataclasses import dataclass
from pathlib import Path

import torch
from pyannote.audio import Pipeline
from pyannote.core import Annotation

from stt.config import DiarizeConfig, WhisperConfig
from stt.whisper_common import post_whisper_remote, run_whisper_local

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


def _get_whisper_segments_local(
    audio_path: Path, config: WhisperConfig
) -> list[tuple[float, float, str]]:
    """Get transcription segments with timestamps using local whisper."""
    segments, _info = run_whisper_local(audio_path, config)
    return [(seg.start, seg.end, seg.text.strip()) for seg in segments]


def _get_whisper_segments_remote(
    audio_path: Path, config: WhisperConfig
) -> list[tuple[float, float, str]]:
    """Get transcription segments with timestamps from remote faster-whisper-server."""
    try:
        response = post_whisper_remote(
            audio_path, config, response_format="verbose_json"
        )
    except ValueError as e:
        raise DiarizationError(str(e)) from e

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


def _run_diarization(audio_path: Path, config: DiarizeConfig) -> Annotation:
    """Run pyannote speaker diarization on audio.

    Returns an Annotation object with .itertracks() support.
    pyannote v4 returns a DiarizeOutput dataclass; we unwrap it.
    """
    pipeline = Pipeline.from_pretrained(config.model_name, token=config.hf_token)

    if config.device != "cpu":
        pipeline.to(torch.device(config.device))

    result = pipeline(str(audio_path))

    # pyannote v4 returns DiarizeOutput, extract the Annotation
    if hasattr(result, "speaker_diarization"):
        return result.speaker_diarization
    return result


def _assign_speaker(start: float, end: float, diarization: Annotation) -> str:
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
        normalized = []
        for seg in result:
            if seg.speaker not in speaker_map:
                speaker_map[seg.speaker] = f"Sprecher {len(speaker_map) + 1}"
            normalized.append(
                DiarizedSegment(
                    speaker=speaker_map[seg.speaker],
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                )
            )

        logger.info(
            "Diarization complete: %d segments, %d speakers",
            len(normalized),
            len(speaker_map),
        )
        return normalized
    except DiarizationError:
        raise
    except (RuntimeError, OSError) as e:
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
