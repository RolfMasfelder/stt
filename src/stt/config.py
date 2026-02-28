"""Configuration management for the STT project."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WhisperConfig:
    """Configuration for the Whisper speech-to-text model."""

    model_name: str = "small"
    device: str = "cpu"


@dataclass(frozen=True)
class LMStudioConfig:
    """Configuration for the LM Studio API connection."""

    host: str = "localhost"
    port: int = 1234
    model: str = "mistral-7b-instruct"

    @property
    def url(self) -> str:
        """Return the full API URL for chat completions."""
        return f"http://{self.host}:{self.port}/v1/chat/completions"


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    lm_studio: LMStudioConfig = field(default_factory=LMStudioConfig)
    audio_input_dir: Path = Path("./audio")
    output_dir: Path = Path("./output")
    log_level: str = "INFO"


def load_config(env_file: str | None = None) -> AppConfig:
    """Load configuration from environment variables.

    Args:
        env_file: Optional path to a .env file. If None, tries to load
                  from the default .env location.

    Returns:
        A fully populated AppConfig instance.
    """
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    whisper = WhisperConfig(
        model_name=os.getenv("WHISPER_MODEL", "small"),
        device=os.getenv("WHISPER_DEVICE", "cpu"),
    )

    lm_studio_port = os.getenv("LM_STUDIO_PORT", "1234")
    lm_studio = LMStudioConfig(
        host=os.getenv("LM_STUDIO_HOST", "localhost"),
        port=int(lm_studio_port),
        model=os.getenv("LM_STUDIO_MODEL", "mistral-7b-instruct"),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    config = AppConfig(
        whisper=whisper,
        lm_studio=lm_studio,
        audio_input_dir=Path(os.getenv("AUDIO_INPUT_DIR", "./audio")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "./output")),
        log_level=log_level,
    )

    logger.debug("Configuration loaded: %s", config)
    return config
