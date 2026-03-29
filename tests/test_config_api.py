"""Tests for StorageConfig API endpoints (2b.2)."""

import uuid
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from stt.api.models import AuditLog, StorageConfig
from stt.api.storage import StorageTestResult


@pytest.fixture
def local_config() -> StorageConfig:
    return StorageConfig.objects.create(
        name="test-local",
        backend_type="local",
        base_path="/tmp/stt-test",
    )


@pytest.fixture
def s3_config() -> StorageConfig:
    return StorageConfig.objects.create(
        name="test-s3",
        backend_type="s3",
        s3_endpoint_url="https://s3.example.com",
        s3_bucket="test-bucket",
        s3_access_key="AKIATEST",
        s3_secret_key="secret123",
        s3_region="eu-central-1",
    )


@pytest.mark.django_db
class TestStorageConfigList:
    """GET /v1/config/storage — list all storage configs."""

    def test_list_empty(self, auth_client: APIClient) -> None:
        resp = auth_client.get("/v1/config/storage")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_configs(
        self, auth_client: APIClient, local_config: StorageConfig
    ) -> None:
        resp = auth_client.get("/v1/config/storage")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-local"
        assert data[0]["backend_type"] == "local"

    def test_list_hides_s3_secret(
        self, auth_client: APIClient, s3_config: StorageConfig
    ) -> None:
        resp = auth_client.get("/v1/config/storage")
        data = resp.json()
        assert len(data) == 1
        assert "s3_secret_key" not in data[0]


@pytest.mark.django_db
class TestStorageConfigDetail:
    """GET /v1/config/storage/{id} — single config."""

    def test_get_detail(
        self, auth_client: APIClient, local_config: StorageConfig
    ) -> None:
        resp = auth_client.get(f"/v1/config/storage/{local_config.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(local_config.id)

    def test_get_not_found(self, auth_client: APIClient) -> None:
        fake_id = uuid.uuid4()
        resp = auth_client.get(f"/v1/config/storage/{fake_id}")
        assert resp.status_code == 404

    def test_get_invalid_uuid(self, auth_client: APIClient) -> None:
        resp = auth_client.get("/v1/config/storage/not-a-uuid")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestStorageConfigCreate:
    """POST /v1/config/storage — create a config."""

    def test_create_local(self, auth_client: APIClient) -> None:
        payload = {
            "name": "new-local",
            "backend_type": "local",
            "base_path": "/data/audio",
        }
        resp = auth_client.post("/v1/config/storage", data=payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "new-local"
        assert data["backend_type"] == "local"
        assert "id" in data
        assert StorageConfig.objects.filter(id=data["id"]).exists()

    def test_create_s3(self, auth_client: APIClient) -> None:
        payload = {
            "name": "new-s3",
            "backend_type": "s3",
            "s3_endpoint_url": "https://s3.eu.example.com",
            "s3_bucket": "my-bucket",
            "s3_access_key": "AKIA123",
            "s3_secret_key": "supersecret",
            "s3_region": "eu-central-1",
        }
        resp = auth_client.post("/v1/config/storage", data=payload, format="json")
        assert resp.status_code == 201
        # Secret NOT in response
        assert "s3_secret_key" not in resp.json()
        # But stored in DB
        cfg = StorageConfig.objects.get(id=resp.json()["id"])
        assert cfg.s3_secret_key == "supersecret"

    def test_create_invalid(self, auth_client: APIClient) -> None:
        resp = auth_client.post("/v1/config/storage", data={}, format="json")
        assert resp.status_code == 400

    def test_create_audit_log(self, auth_client: APIClient) -> None:
        payload = {
            "name": "audit-test",
            "backend_type": "local",
            "base_path": "/tmp",
        }
        auth_client.post("/v1/config/storage", data=payload, format="json")
        assert AuditLog.objects.filter(action="storage_config_created").exists()


@pytest.mark.django_db
class TestStorageConfigUpdate:
    """PUT /v1/config/storage/{id} — update a config."""

    def test_update(self, auth_client: APIClient, local_config: StorageConfig) -> None:
        resp = auth_client.put(
            f"/v1/config/storage/{local_config.id}",
            data={"name": "updated-name"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated-name"
        local_config.refresh_from_db()
        assert local_config.name == "updated-name"

    def test_update_not_found(self, auth_client: APIClient) -> None:
        fake_id = uuid.uuid4()
        resp = auth_client.put(
            f"/v1/config/storage/{fake_id}",
            data={"name": "x"},
            format="json",
        )
        assert resp.status_code == 404

    def test_update_audit_log(
        self, auth_client: APIClient, local_config: StorageConfig
    ) -> None:
        auth_client.put(
            f"/v1/config/storage/{local_config.id}",
            data={"name": "changed"},
            format="json",
        )
        assert AuditLog.objects.filter(action="storage_config_updated").exists()


@pytest.mark.django_db
class TestStorageConfigDelete:
    """DELETE /v1/config/storage/{id} — delete a config."""

    def test_delete(self, auth_client: APIClient, local_config: StorageConfig) -> None:
        config_id = local_config.id
        resp = auth_client.delete(f"/v1/config/storage/{config_id}")
        assert resp.status_code == 204
        assert not StorageConfig.objects.filter(id=config_id).exists()

    def test_delete_not_found(self, auth_client: APIClient) -> None:
        fake_id = uuid.uuid4()
        resp = auth_client.delete(f"/v1/config/storage/{fake_id}")
        assert resp.status_code == 404

    def test_delete_audit_log(
        self, auth_client: APIClient, local_config: StorageConfig
    ) -> None:
        auth_client.delete(f"/v1/config/storage/{local_config.id}")
        assert AuditLog.objects.filter(action="storage_config_deleted").exists()


@pytest.mark.django_db
class TestStorageConfigTest:
    """POST /v1/config/storage/{id}/test — test backend connectivity."""

    def test_success(self, auth_client: APIClient, local_config: StorageConfig) -> None:
        test_result = StorageTestResult(
            connection=True,
            write=True,
            read=True,
            delete=True,
            message="All checks passed",
            duration_ms=42,
        )
        with patch("stt.api.storage.get_backend") as mock_get:
            mock_get.return_value.test_connection.return_value = test_result
            resp = auth_client.post(f"/v1/config/storage/{local_config.id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["checks"]["connection"] is True
        assert data["duration_ms"] == 42

    def test_failure(self, auth_client: APIClient, local_config: StorageConfig) -> None:
        test_result = StorageTestResult(
            connection=True,
            write=False,
            read=False,
            delete=False,
            message="Write failed: permission denied",
            duration_ms=5,
        )
        with patch("stt.api.storage.get_backend") as mock_get:
            mock_get.return_value.test_connection.return_value = test_result
            resp = auth_client.post(f"/v1/config/storage/{local_config.id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert data["checks"]["write"] is False

    def test_not_found(self, auth_client: APIClient) -> None:
        fake_id = uuid.uuid4()
        resp = auth_client.post(f"/v1/config/storage/{fake_id}/test")
        assert resp.status_code == 404

    def test_backend_error(
        self, auth_client: APIClient, s3_config: StorageConfig
    ) -> None:
        from stt.api.storage import StorageError

        with patch(
            "stt.api.storage.get_backend",
            side_effect=StorageError("S3 backend not yet implemented"),
        ):
            resp = auth_client.post(f"/v1/config/storage/{s3_config.id}/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "not yet implemented" in data["message"]

    def test_audit_log(
        self, auth_client: APIClient, local_config: StorageConfig
    ) -> None:
        test_result = StorageTestResult(
            connection=True,
            write=True,
            read=True,
            delete=True,
            message="OK",
            duration_ms=1,
        )
        with patch("stt.api.storage.get_backend") as mock_get:
            mock_get.return_value.test_connection.return_value = test_result
            auth_client.post(f"/v1/config/storage/{local_config.id}/test")
        assert AuditLog.objects.filter(action="storage_config_tested").exists()
