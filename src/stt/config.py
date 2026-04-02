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
class LLMConfig:
    """Configuration for the LLM API connection (Ollama or compatible)."""

    base_url: str = "http://localhost:11434"
    model: str = "mistral"
    timeout: int = 120

    @property
    def url(self) -> str:
        """Return the full API URL for chat completions."""
        base = self.base_url.rstrip("/")
        return f"{base}/v1/chat/completions"


@dataclass(frozen=True)
class MLServiceConfig:
    """Configuration for the ML microservice (transcription + diarization)."""

    base_url: str = "http://stt-ml:8091"
    timeout: int = 600


@dataclass(frozen=True)
class OAuth2ClientConfig:
    """OAuth2 Client Credentials configuration for CLI/client access."""

    client_id: str = ""
    client_secret: str = ""
    token_url: str = ""
    scopes: str = "read write"


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration."""

    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    diarize: DiarizeConfig = field(default_factory=DiarizeConfig)
    ml_service: MLServiceConfig = field(default_factory=MLServiceConfig)
    oauth2: OAuth2ClientConfig = field(default_factory=OAuth2ClientConfig)
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

    llm_timeout = os.getenv("LLM_TIMEOUT", "120")
    llm = LLMConfig(
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434"),
        model=os.getenv("LLM_MODEL", "mistral"),
        timeout=int(llm_timeout),
    )

    diarize = DiarizeConfig(
        hf_token=os.getenv("HF_STT_TOKEN") or None,
        model_name=os.getenv("DIARIZE_MODEL", "pyannote/speaker-diarization-3.1"),
        device=os.getenv("DIARIZE_DEVICE", "cpu"),
    )

    ml_service_timeout = os.getenv("ML_SERVICE_TIMEOUT", "600")
    ml_service = MLServiceConfig(
        base_url=os.getenv("ML_SERVICE_URL", "http://stt-ml:8091"),
        timeout=int(ml_service_timeout),
    )

    log_level = os.getenv("LOG_LEVEL", "INFO")

    stt_server_url = os.getenv("STT_SERVER_URL") or None

    oauth2 = OAuth2ClientConfig(
        client_id=os.getenv("OAUTH2_CLIENT_ID", ""),
        client_secret=os.getenv("OAUTH2_CLIENT_SECRET", ""),
        token_url=os.getenv("OAUTH2_TOKEN_URL", ""),
        scopes=os.getenv("OAUTH2_SCOPES", "read write"),
    )

    config = AppConfig(
        whisper=whisper,
        llm=llm,
        diarize=diarize,
        ml_service=ml_service,
        oauth2=oauth2,
        audio_input_dir=Path(os.getenv("AUDIO_INPUT_DIR", "./data/audio")),
        output_dir=Path(os.getenv("OUTPUT_DIR", "./data/output")),
        log_level=log_level,
        stt_server_url=stt_server_url,
    )

    _log_config(config)
    return config


def _log_config(cfg: AppConfig) -> None:
    """Log configuration with sensitive values masked."""
    config_str = str(cfg)
    if cfg.diarize.hf_token:
        config_str = config_str.replace(cfg.diarize.hf_token, "***")
    if cfg.oauth2.client_secret:
        config_str = config_str.replace(cfg.oauth2.client_secret, "***")
    logger.debug("Configuration loaded: %s", config_str)
