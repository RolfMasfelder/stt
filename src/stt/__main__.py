"""CLI entry point for the STT application."""

import argparse
import logging
import sys
from pathlib import Path

from stt.config import load_config
from stt.logging_setup import setup_logging
from stt.summarize import (
    SummarizationError,
    diarize_text,  # noqa: F401 (used with --diarize standalone)
    process_transcript,
    summarize_text,
)
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
        "--process",
        action="store_true",
        help="Full pipeline: structure into sections, then summarize",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help="Identify speakers in the transcript (adds speaker labels)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write transcript to file instead of stdout",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=None,
        help="LM Studio request timeout in seconds (overrides .env)",
    )
    parser.add_argument(
        "--whisper-timeout",
        type=int,
        default=None,
        help="Whisper transcription timeout in seconds (overrides .env)",
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

    # Override timeouts from CLI if provided
    if args.timeout is not None or args.whisper_timeout is not None:
        from dataclasses import replace

        if args.timeout is not None:
            config = replace(
                config,
                lm_studio=replace(config.lm_studio, timeout=args.timeout),
            )
        if args.whisper_timeout is not None:
            config = replace(
                config,
                whisper=replace(config.whisper, timeout=args.whisper_timeout),
            )

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

    # Full pipeline: structure + summarize (+ optional diarize)
    if args.process:
        try:
            structured, summary, diarized = process_transcript(
                transcript, config.lm_studio, diarize=args.diarize
            )

            if diarized:
                print("\n--- Sprecherzuordnung ---")
                print(diarized)

            print("\n--- Strukturierung ---")
            print(structured)
            print("\n--- Zusammenfassung ---")
            print(summary)

            # Save results to output dir if configured
            if args.output:
                stem = args.output.stem
                out_dir = args.output.parent
                out_dir.mkdir(parents=True, exist_ok=True)

                if diarized:
                    diarized_path = out_dir / f"{stem}_sprecher.md"
                    diarized_path.write_text(diarized, encoding="utf-8")
                    logger.info("Diarized text written to %s", diarized_path)

                structured_path = out_dir / f"{stem}_struktur.md"
                structured_path.write_text(structured, encoding="utf-8")
                logger.info("Structured text written to %s", structured_path)

                summary_path = out_dir / f"{stem}_zusammenfassung.md"
                summary_path.write_text(summary, encoding="utf-8")
                logger.info("Summary written to %s", summary_path)
        except SummarizationError as e:
            logger.error("Processing failed: %s", e)
            return 1

    # Standalone diarize (without --process)
    elif args.diarize:
        try:
            diarized = diarize_text(transcript, config.lm_studio)
            print("\n--- Sprecherzuordnung ---")
            print(diarized)

            if args.output:
                stem = args.output.stem
                out_dir = args.output.parent
                out_dir.mkdir(parents=True, exist_ok=True)
                diarized_path = out_dir / f"{stem}_sprecher.md"
                diarized_path.write_text(diarized, encoding="utf-8")
                logger.info("Diarized text written to %s", diarized_path)
        except SummarizationError as e:
            logger.error("Diarization failed: %s", e)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
