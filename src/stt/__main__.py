"""CLI entry point for the STT application."""

import argparse
import logging
import sys
from pathlib import Path

from stt.config import load_config
from stt.logging_setup import setup_logging
from stt.summarize import SummarizationError, summarize_text
from stt.transcribe import TranscriptionError, transcribe_audio

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Lokale Meeting-Transkription und Zusammenfassung",
    )
    parser.add_argument(
        "audio_file",
        nargs="?",
        help="Path to the audio file to transcribe",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Also summarize the transcript via LM Studio",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write transcript to file instead of stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Command line arguments. Uses sys.argv if None.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    args = parse_args(argv)
    config = load_config()
    setup_logging(config.log_level)

    # Determine audio file path
    if args.audio_file:
        audio_path = Path(args.audio_file)
    else:
        # Look for files in the configured audio input directory
        audio_dir = config.audio_input_dir
        wav_files = sorted(audio_dir.glob("*.wav"))
        if not wav_files:
            logger.error(
                "No audio file specified and no .wav files found in %s", audio_dir
            )
            return 1
        audio_path = wav_files[0]
        logger.info("No audio file specified, using: %s", audio_path)

    # Transcribe
    try:
        transcript = transcribe_audio(audio_path, config.whisper)
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1
    except TranscriptionError as e:
        logger.error("Transcription failed: %s", e)
        return 1

    # Output transcript
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(transcript, encoding="utf-8")
        logger.info("Transcript written to %s", args.output)
    else:
        print(transcript)

    # Optionally summarize
    if args.summarize:
        try:
            summary = summarize_text(transcript, config.lm_studio)
            print("\n--- Zusammenfassung ---")
            print(summary)
        except SummarizationError as e:
            logger.error("Summarization failed: %s", e)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
