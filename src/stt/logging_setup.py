"""Logging configuration for the STT project."""

import logging
import sys
import warnings


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the application.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Suppress noisy torchcodec warning from pyannote when no GPU is available
    warnings.filterwarnings("ignore", message="torchcodec is not installed correctly")
