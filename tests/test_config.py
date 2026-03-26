"""Tests for the configuration module."""

import os
from unittest.mock import patch

from stt.config import (
    AppConfig,
    DiarizeConfig,
    LMStudioConfig,
    WhisperConfig,
    load_config,
)


class TestWhisperConfig:
    """Tests for WhisperConfig."""

    def test_defaults(self) -> None:
        config = WhisperConfig()
        assert config.model_name == "small"
        assert config.device == "cpu"
        assert config.api_url is None
        assert config.timeout == 600

    def test_custom_values(self) -> None:
        config = WhisperConfig(model_name="large-v3", device="cuda")
        assert config.model_name == "large-v3"
        assert config.device == "cuda"

    def test_api_url(self) -> None:
        config = WhisperConfig(api_url="http://192.168.178.80:8000")
        assert config.api_url == "http://192.168.178.80:8000"


class TestLMStudioConfig:
    """Tests for LMStudioConfig."""

    def test_defaults(self) -> None:
        config = LMStudioConfig()
        assert config.host == "localhost"
        assert config.port == 1234
        assert config.model == "mistral-7b-instruct"
        assert config.timeout == 120

    def test_url_property(self) -> None:
        config = LMStudioConfig(host="myhost", port=5678)
        assert config.url == "http://myhost:5678/v1/chat/completions"

    def test_custom_timeout(self) -> None:
        config = LMStudioConfig(timeout=600)
        assert config.timeout == 600


class TestDiarizeConfig:
    """Tests for DiarizeConfig."""

    def test_defaults(self) -> None:
        config = DiarizeConfig()
        assert config.hf_token is None
        assert config.model_name == "pyannote/speaker-diarization-3.1"
        assert config.device == "cpu"

    def test_custom_values(self) -> None:
        config = DiarizeConfig(hf_token="hf_test", device="cuda")
        assert config.hf_token == "hf_test"
        assert config.device == "cuda"


class TestLoadConfig:
    """Tests for load_config."""

    @patch.dict(
        os.environ,
        {
            "WHISPER_MODEL": "large-v3",
            "WHISPER_DEVICE": "cuda",
            "WHISPER_API_URL": "http://192.168.178.80:8000",
            "WHISPER_TIMEOUT": "1800",
            "LM_STUDIO_HOST": "testhost",
            "LM_STUDIO_PORT": "9999",
            "LM_STUDIO_MODEL": "test-model",
            "LM_STUDIO_TIMEOUT": "300",
            "HF_STT_TOKEN": "hf_test123",
            "DIARIZE_MODEL": "pyannote/speaker-diarization-3.0",
            "DIARIZE_DEVICE": "cuda",
            "LOG_LEVEL": "DEBUG",
            "AUDIO_INPUT_DIR": "/tmp/audio",
            "OUTPUT_DIR": "/tmp/output",
        },
        clear=False,
    )
    def test_load_from_env(self) -> None:
        config = load_config(env_file="/dev/null")
        assert config.whisper.model_name == "large-v3"
        assert config.whisper.device == "cuda"
        assert config.whisper.api_url == "http://192.168.178.80:8000"
        assert config.whisper.timeout == 1800
        assert config.lm_studio.host == "testhost"
        assert config.lm_studio.port == 9999
        assert config.lm_studio.model == "test-model"
        assert config.lm_studio.timeout == 300
        assert config.diarize.hf_token == "hf_test123"
        assert config.diarize.model_name == "pyannote/speaker-diarization-3.0"
        assert config.diarize.device == "cuda"
        assert config.log_level == "DEBUG"

    @patch.dict(os.environ, {}, clear=True)
    def test_load_defaults(self) -> None:
        config = load_config(env_file="/dev/null")
        assert config.whisper.model_name == "small"
        assert config.whisper.api_url is None
        assert config.whisper.timeout == 600
        assert config.lm_studio.host == "localhost"
        assert config.lm_studio.timeout == 120
        assert config.diarize.hf_token is None
        assert config.diarize.model_name == "pyannote/speaker-diarization-3.1"
        assert config.log_level == "INFO"

    def test_app_config_defaults(self) -> None:
        config = AppConfig()
        assert config.log_level == "INFO"
