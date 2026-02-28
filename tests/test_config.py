"""Tests for the configuration module."""

import os
from unittest.mock import patch

from stt.config import AppConfig, LMStudioConfig, WhisperConfig, load_config


class TestWhisperConfig:
    """Tests for WhisperConfig."""

    def test_defaults(self) -> None:
        config = WhisperConfig()
        assert config.model_name == "small"
        assert config.device == "cpu"

    def test_custom_values(self) -> None:
        config = WhisperConfig(model_name="large-v3", device="cuda")
        assert config.model_name == "large-v3"
        assert config.device == "cuda"


class TestLMStudioConfig:
    """Tests for LMStudioConfig."""

    def test_defaults(self) -> None:
        config = LMStudioConfig()
        assert config.host == "localhost"
        assert config.port == 1234
        assert config.model == "mistral-7b-instruct"

    def test_url_property(self) -> None:
        config = LMStudioConfig(host="myhost", port=5678)
        assert config.url == "http://myhost:5678/v1/chat/completions"


class TestLoadConfig:
    """Tests for load_config."""

    @patch.dict(
        os.environ,
        {
            "WHISPER_MODEL": "large-v3",
            "WHISPER_DEVICE": "cuda",
            "LM_STUDIO_HOST": "testhost",
            "LM_STUDIO_PORT": "9999",
            "LM_STUDIO_MODEL": "test-model",
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
        assert config.lm_studio.host == "testhost"
        assert config.lm_studio.port == 9999
        assert config.lm_studio.model == "test-model"
        assert config.log_level == "DEBUG"

    @patch.dict(os.environ, {}, clear=True)
    def test_load_defaults(self) -> None:
        config = load_config(env_file="/dev/null")
        assert config.whisper.model_name == "small"
        assert config.lm_studio.host == "localhost"
        assert config.log_level == "INFO"

    def test_app_config_defaults(self) -> None:
        config = AppConfig()
        assert config.log_level == "INFO"
