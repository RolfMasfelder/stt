"""Tests for the configuration module."""

import os
from unittest.mock import patch

from stt.config import (
    AppConfig,
    DiarizeConfig,
    LLMConfig,
    MLServiceConfig,
    OAuth2ClientConfig,
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


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_defaults(self) -> None:
        config = LLMConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "mistral"
        assert config.timeout == 120

    def test_url_property(self) -> None:
        config = LLMConfig(base_url="http://myhost:11434")
        assert config.url == "http://myhost:11434/v1/chat/completions"

    def test_custom_timeout(self) -> None:
        config = LLMConfig(timeout=600)
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


class TestMLServiceConfig:
    """Tests for MLServiceConfig."""

    def test_defaults(self) -> None:
        config = MLServiceConfig()
        assert config.base_url == "http://stt-ml:8091"
        assert config.timeout == 600

    def test_custom_values(self) -> None:
        config = MLServiceConfig(base_url="http://localhost:8091", timeout=300)
        assert config.base_url == "http://localhost:8091"
        assert config.timeout == 300


class TestLoadConfig:
    """Tests for load_config."""

    @patch.dict(
        os.environ,
        {
            "WHISPER_MODEL": "large-v3",
            "WHISPER_DEVICE": "cuda",
            "WHISPER_API_URL": "http://192.168.178.80:8000",
            "WHISPER_TIMEOUT": "1800",
            "LLM_BASE_URL": "http://testhost:11434",
            "LLM_MODEL": "test-model",
            "LLM_TIMEOUT": "300",
            "HF_STT_TOKEN": "hf_test123",
            "DIARIZE_MODEL": "pyannote/speaker-diarization-3.0",
            "DIARIZE_DEVICE": "cuda",
            "ML_SERVICE_URL": "http://ml:9000",
            "ML_SERVICE_TIMEOUT": "1200",
            "LOG_LEVEL": "DEBUG",
            "AUDIO_INPUT_DIR": "/tmp/audio",
            "OUTPUT_DIR": "/tmp/output",
            "STT_SERVER_URL": "http://192.168.178.80:8001",
            "OAUTH2_CLIENT_ID": "my-client",
            "OAUTH2_CLIENT_SECRET": "my-secret",
            "OAUTH2_TOKEN_URL": "http://192.168.178.80:8001/o/token/",
            "OAUTH2_SCOPES": "read",
        },
        clear=False,
    )
    def test_load_from_env(self) -> None:
        config = load_config(env_file="/dev/null")
        assert config.whisper.model_name == "large-v3"
        assert config.whisper.device == "cuda"
        assert config.whisper.api_url == "http://192.168.178.80:8000"
        assert config.whisper.timeout == 1800
        assert config.llm.base_url == "http://testhost:11434"
        assert config.llm.model == "test-model"
        assert config.llm.timeout == 300
        assert config.diarize.hf_token == "hf_test123"
        assert config.diarize.model_name == "pyannote/speaker-diarization-3.0"
        assert config.diarize.device == "cuda"
        assert config.ml_service.base_url == "http://ml:9000"
        assert config.ml_service.timeout == 1200
        assert config.log_level == "DEBUG"
        assert config.stt_server_url == "http://192.168.178.80:8001"
        assert config.oauth2.client_id == "my-client"
        assert config.oauth2.client_secret == "my-secret"
        assert config.oauth2.token_url == "http://192.168.178.80:8001/o/token/"
        assert config.oauth2.scopes == "read"

    @patch.dict(os.environ, {}, clear=True)
    def test_load_defaults(self) -> None:
        config = load_config(env_file="/dev/null")
        assert config.whisper.model_name == "small"
        assert config.whisper.api_url is None
        assert config.whisper.timeout == 600
        assert config.llm.base_url == "http://localhost:11434"
        assert config.llm.timeout == 120
        assert config.diarize.hf_token is None
        assert config.diarize.model_name == "pyannote/speaker-diarization-3.1"
        assert config.ml_service.base_url == "http://stt-ml:8091"
        assert config.ml_service.timeout == 600
        assert config.log_level == "INFO"
        assert config.stt_server_url is None
        assert config.oauth2.client_id == ""
        assert config.oauth2.token_url == ""
        assert config.oauth2.scopes == "read write"

    def test_app_config_defaults(self) -> None:
        config = AppConfig()
        assert config.log_level == "INFO"
        assert config.stt_server_url is None
        assert config.oauth2.client_id == ""


class TestOAuth2ClientConfig:
    """Tests for OAuth2ClientConfig."""

    def test_defaults(self) -> None:
        config = OAuth2ClientConfig()
        assert config.client_id == ""
        assert config.client_secret == ""
        assert config.token_url == ""
        assert config.scopes == "read write"

    def test_custom_values(self) -> None:
        config = OAuth2ClientConfig(
            client_id="abc",
            client_secret="secret",
            token_url="https://example.com/o/token/",
            scopes="read",
        )
        assert config.client_id == "abc"
        assert config.client_secret == "secret"
        assert config.token_url == "https://example.com/o/token/"
        assert config.scopes == "read"
