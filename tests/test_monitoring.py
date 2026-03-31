"""Tests for Prometheus monitoring integration (2f.6)."""

import pytest

from stt.api.metrics import (
    GDPR_DELETED,
    JOB_DURATION,
    JOBS_COMPLETED,
    JOBS_CREATED,
    JOBS_FAILED,
)


class TestMetricsEndpoint:
    """Verify the /metrics endpoint is accessible."""

    @pytest.mark.django_db
    def test_metrics_endpoint_returns_200(self, client: object) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_metrics_contains_django_prometheus(self, client: object) -> None:
        response = client.get("/metrics")
        body = response.content.decode()
        assert "django_http" in body

    @pytest.mark.django_db
    def test_metrics_contains_stt_custom(self, client: object) -> None:
        response = client.get("/metrics")
        body = response.content.decode()
        assert "stt_jobs_created_total" in body


class TestCustomMetrics:
    """Verify custom STT metrics are properly defined."""

    def test_jobs_created_counter(self) -> None:
        assert JOBS_CREATED._name == "stt_jobs_created"

    def test_jobs_completed_counter(self) -> None:
        assert JOBS_COMPLETED._name == "stt_jobs_completed"

    def test_jobs_failed_counter(self) -> None:
        assert JOBS_FAILED._name == "stt_jobs_failed"

    def test_job_duration_histogram(self) -> None:
        assert JOB_DURATION._name == "stt_job_duration_seconds"

    def test_gdpr_deleted_counter(self) -> None:
        assert GDPR_DELETED._name == "stt_gdpr_auto_deleted"


class TestPrometheusMiddleware:
    """Verify Prometheus middleware is correctly positioned."""

    def test_before_middleware_first(self) -> None:
        from django.conf import settings

        assert settings.MIDDLEWARE[0] == (
            "django_prometheus.middleware.PrometheusBeforeMiddleware"
        )

    def test_after_middleware_last(self) -> None:
        from django.conf import settings

        assert settings.MIDDLEWARE[-1] == (
            "django_prometheus.middleware.PrometheusAfterMiddleware"
        )

    def test_django_prometheus_in_installed_apps(self) -> None:
        from django.conf import settings

        assert "django_prometheus" in settings.INSTALLED_APPS
