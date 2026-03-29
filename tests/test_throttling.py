"""Tests for rate limiting / throttling (ADR-14)."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from stt.config import DiarizeConfig, LMStudioConfig, WhisperConfig


def _mock_config():
    mock_config = MagicMock()
    mock_config.log_level = "WARNING"
    mock_config.whisper = WhisperConfig()
    mock_config.diarize = DiarizeConfig(hf_token="hf_test")
    mock_config.lm_studio = LMStudioConfig()
    return mock_config


def _audio_file():
    f = BytesIO(b"fake audio data")
    f.name = "test.wav"
    return f


class TestThrottleSettings:
    """Verify throttle configuration."""

    def test_throttle_classes_configured(self) -> None:
        from django.conf import settings

        throttle_classes = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]
        assert "rest_framework.throttling.AnonRateThrottle" in throttle_classes
        assert "rest_framework.throttling.UserRateThrottle" in throttle_classes

    def test_throttle_rates_configured(self) -> None:
        from django.conf import settings

        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        assert "anon" in rates
        assert "user" in rates
        assert "upload" in rates
        assert rates["upload"] == "10/minute"

    def test_upload_views_have_throttle(self) -> None:
        from stt.api.throttles import UploadRateThrottle
        from stt.api.views import (
            DiarizeView,
            JobCreateView,
            ProcessView,
            TranscribeView,
        )

        for view_class in [TranscribeView, DiarizeView, ProcessView, JobCreateView]:
            assert UploadRateThrottle in view_class.throttle_classes, (
                f"{view_class.__name__} missing UploadRateThrottle"
            )


@pytest.mark.django_db
class TestUploadThrottling:
    """Verify upload endpoints are rate-limited."""

    @patch("stt.api.views.transcribe_audio", return_value="text")
    @patch("stt.api.throttles.UploadRateThrottle.get_rate", return_value="2/minute")
    def test_upload_throttle_limits_requests(
        self, mock_rate, mock_transcribe, auth_client
    ) -> None:
        """After exceeding upload rate, requests should be throttled (429)."""
        from django.core.cache import cache

        cache.clear()

        with patch("stt.api.views._get_config", return_value=_mock_config()):
            # First 2 should succeed (rate=2/min)
            for _ in range(2):
                response = auth_client.post(
                    "/v1/transcribe",
                    {"file": _audio_file()},
                    format="multipart",
                )
                assert response.status_code == 200

            # Third should be throttled
            response = auth_client.post(
                "/v1/transcribe",
                {"file": _audio_file()},
                format="multipart",
            )
            assert response.status_code == 429

        cache.clear()
