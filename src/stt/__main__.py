"""CLI entry point for the STT application."""

import argparse
import logging
import sys
from pathlib import Path

from stt.client import ClientError, STTClient
from stt.config import load_config
from stt.diarize import DiarizationError, diarize_audio, format_diarized_segments
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
    parser.add_argument(
        "--skip",
        action="store_true",
        help="Skip speech-to-text transcription (requires --text-file)",
    )
    parser.add_argument(
        "--text-file",
        type=Path,
        default=None,
        help="Path to an existing text file to use instead of transcription",
    )
    return parser.parse_args(argv)


def _run_remote(args: argparse.Namespace, config) -> int:
    """Run processing via the remote STT server."""
    client = STTClient(config.stt_server_url, timeout=config.whisper.timeout)

    if not args.audio_file:
        audio_dir = config.audio_input_dir
        wav_files = sorted(audio_dir.glob("*.wav"))
        if not wav_files:
            logger.error(
                "No audio file specified and no .wav files found in %s", audio_dir
            )
            return 1
        audio_path = wav_files[0]
        logger.info("No audio file specified, using: %s", audio_path)
    else:
        audio_path = Path(args.audio_file)

    try:
        if args.process:
            result = client.process(audio_path, diarize=args.diarize)
            transcript = result.text
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(transcript, encoding="utf-8")
                logger.info("Transcript written to %s", args.output)
            else:
                print(transcript)

            if result.diarized_text:
                print("\n--- Sprecherzuordnung ---")
                print(result.diarized_text)
            print("\n--- Strukturierung ---")
            print(result.structured_text)
            print("\n--- Zusammenfassung ---")
            print(result.summary)

            if args.output:
                stem = args.output.stem
                out_dir = args.output.parent
                if result.diarized_text:
                    (out_dir / f"{stem}_sprecher.md").write_text(
                        result.diarized_text, encoding="utf-8"
                    )
                (out_dir / f"{stem}_struktur.md").write_text(
                    result.structured_text, encoding="utf-8"
                )
                (out_dir / f"{stem}_zusammenfassung.md").write_text(
                    result.summary, encoding="utf-8"
                )

        elif args.diarize:
            result = client.diarize(audio_path)
            transcript = result.text
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(transcript, encoding="utf-8")
                logger.info("Transcript written to %s", args.output)
            else:
                print(transcript)
            print("\n--- Sprecherzuordnung ---")
            print(result.diarized_text)
            if args.output:
                stem = args.output.stem
                out_dir = args.output.parent
                (out_dir / f"{stem}_sprecher.md").write_text(
                    result.diarized_text, encoding="utf-8"
                )

        else:
            transcript = client.transcribe(audio_path)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(transcript, encoding="utf-8")
                logger.info("Transcript written to %s", args.output)
            else:
                print(transcript)

            if args.summarize:
                result = client.process(audio_path, diarize=False)
                print("\n--- Zusammenfassung ---")
                print(result.summary)

    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1
    except ClientError as e:
        logger.error("Server request failed: %s", e)
        return 1

    return 0


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

    diarized_text: str | None = None

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

    # --skip mode: read transcript from an existing text file
    if args.skip:
        if not args.text_file:
            logger.error("--skip requires --text-file to be specified")
            return 1
        text_path = Path(args.text_file)
        if not text_path.exists():
            logger.error("Text file not found: %s", text_path)
            return 1
        transcript = text_path.read_text(encoding="utf-8")
        logger.info(
            "Skipping transcription, loaded text from %s (%d characters)",
            text_path,
            len(transcript),
        )

    # Remote server mode: delegate to STT server via HTTP
    elif config.stt_server_url:
        return _run_remote(args, config)

    else:
        # Determine audio file path
        if args.audio_file:
            audio_path = Path(args.audio_file)
        else:
            # Look for files in the configured audio input directory
            audio_dir = config.audio_input_dir
            wav_files = sorted(audio_dir.glob("*.wav"))
            if not wav_files:
                logger.error(
                    "No audio file specified and no .wav files found in %s",
                    audio_dir,
                )
                return 1
            audio_path = wav_files[0]
            logger.info("No audio file specified, using: %s", audio_path)

        # Transcribe + optionally diarize from audio
        if args.diarize and config.diarize.hf_token:
            try:
                segments = diarize_audio(audio_path, config.whisper, config.diarize)
                diarized_text = format_diarized_segments(segments)
                transcript = " ".join(seg.text for seg in segments)
            except FileNotFoundError as e:
                logger.error("%s", e)
                return 1
            except DiarizationError as e:
                logger.error("Diarization failed: %s", e)
                return 1
        else:
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
                transcript,
                config.lm_studio,
                diarize=args.diarize,
                diarized_text=diarized_text,
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
            diarized = diarized_text or diarize_text(transcript, config.lm_studio)
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
