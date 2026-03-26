"""Configuration management for the STT project."""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WhisperConfig:
    """Configuration for the Whisper speech-to-text model.

    When api_url is set, transcription is offloaded to a remote
    faster-whisper-server via its OpenAI-compatible API instead of
    running the model locally.
    """

    model_name: str = "small"
    device: str = "cpu"
    api_url: str | None = None
    timeout: int = 600

    @property
    def transcription_url(self) -> str | None:
        """Return the full URL for the transcriptions endpoint, or None if local."""
        if not self.api_url:
            return None
        url = self.api_url.rstrip("/")
        if not url.endswith("/v1/audio/transcriptions"):
            url += "/v1/audio/transcriptions"
        return url


@dataclass(frozen=True)
class DiarizeConfig:
    """Configuration for pyannote speaker diarization."""

    hf_token: str | None = None
    model_name: str = "pyannote/speaker-diarization-3.1"
    device: str = "cpu"


@dataclass(frozen=True)
class LMStudioConfig:
    """Configuration for the LM Studio API connection."""

    host: str = "localhost"
    port: int = 1234
    model: str = "mistral-7b-instruct"
    timeout: int = 120

    @property
    def url(self) -> str:
        """Return the full API URL for chat completions."""
        return f"http://{self.host}:{self.port}/v1/chat/completions"


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    lm_studio: LMStudioConfig = field(default_factory=LMStudioConfig)
    diarize: DiarizeConfig = field(default_factory=DiarizeConfig)
    audio_input_dir: Path = Path("./data/audio")
    output_dir: Path = Path("./data/output")
    log_level: str = "INFO"
    stt_server_url: str | None = None


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

    whisper_api_url = os.getenv("WHISPER_API_URL") or None
    whisper_timeout = os.getenv("WHISPER_TIMEOUT", "600")
    whisper = WhisperConfig(
        model_name=os.getenv("WHISPER_MODEL", "small"),
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        api_url=whisper_api_url,
        timeout=int(whisper_timeout),
    )

    lm_studio_port = os.getenv("LM_STUDIO_PORT", "1234")
    lm_studio_timeout = os.getenv("LM_STUDIO_TIMEOUT", "120")
    lm_studio = LMStudioConfig(
        host=os.getenv("LM_STUDIO_HOST", "localhost"),
        port=int(lm_studio_port),
        model=os.getenv("LM_STUDIO_MODEL", "mistral-7b-instruct"),
        timeout=int(lm_studio_timeout),
    )

    diarize = DiarizeConfig(
        hf_token=os.getenv("HF_STT_TOKEN") or None,
        model_name=os.getenv("DIARIZE_MODEL", "pyannote/speaker-diarization-3.1"),
        device=os.getenv("DIARIZE_DEVICE", "cpu"),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    stt_server_url = os.getenv("STT_SERVER_URL") or None

    config = AppConfig(
        whisper=whisper,
        lm_studio=lm_studio,
        diarize=diarize,
        audio_input_dir=Path(os.getenv("AUDIO_INPUT_DIR", "./data/audio")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "./data/output")),
        log_level=log_level,
        stt_server_url=stt_server_url,
    )

    logger.debug("Configuration loaded: %s", config)
    return config
