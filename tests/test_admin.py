"""Tests for Django admin Multi-Tenant management (2f.7)."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from stt.api.models import (
    AuditLog,
    Job,
    JobType,
    StorageConfig,
    Tenant,
)


@pytest.fixture
def admin_user(db):
    """Create a superuser for admin access."""
    User = get_user_model()
    return User.objects.create_superuser(
        username="admin", password="adminpass123", email="admin@test.local"
    )


@pytest.fixture
def admin_client(admin_user) -> Client:
    """Django test client logged in as superuser."""
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def sample_tenant(db) -> Tenant:
    return Tenant.objects.create(name="Test Tenant", slug="test-tenant")


@pytest.fixture
def sample_job(db, sample_tenant, admin_user) -> Job:
    return Job.objects.create(
        job_type=JobType.TRANSCRIBE,
        original_filename="test.wav",
        tenant=sample_tenant,
        owner=admin_user,
    )


@pytest.fixture
def sample_storage(db, sample_tenant) -> StorageConfig:
    return StorageConfig.objects.create(
        name="Test S3",
        backend_type="s3",
        tenant=sample_tenant,
        s3_endpoint_url="https://s3.example.com",
        s3_bucket="test-bucket",
        s3_access_key="AKIAIOSFODNN7EXAMPLE",
        s3_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    )


@pytest.fixture
def sample_audit(db, sample_tenant) -> AuditLog:
    return AuditLog.objects.create(
        action="job_created",
        resource_type="job",
        resource_id="12345",
        actor="testuser",
        tenant=sample_tenant,
    )


# -- Registration tests --


class TestAdminRegistration:
    """All models must be registered in admin."""

    @pytest.mark.parametrize(
        "model_name",
        ["tenant", "job", "storageconfig", "auditlog", "resultversion"],
    )
    def test_model_registered(self, admin_client: Client, model_name: str) -> None:
        url = f"/admin/api/{model_name}/"
        response = admin_client.get(url)
        assert response.status_code == 200


# -- Changelist tests --


class TestAdminChangelistPages:
    """Changelist pages must load without errors."""

    def test_tenant_changelist(
        self, admin_client: Client, sample_tenant: Tenant
    ) -> None:
        response = admin_client.get("/admin/api/tenant/")
        assert response.status_code == 200
        assert b"Test Tenant" in response.content

    def test_job_changelist(self, admin_client: Client, sample_job: Job) -> None:
        response = admin_client.get("/admin/api/job/")
        assert response.status_code == 200
        assert b"test.wav" in response.content

    def test_storage_changelist(
        self, admin_client: Client, sample_storage: StorageConfig
    ) -> None:
        response = admin_client.get("/admin/api/storageconfig/")
        assert response.status_code == 200
        assert b"Test S3" in response.content

    def test_auditlog_changelist(
        self, admin_client: Client, sample_audit: AuditLog
    ) -> None:
        response = admin_client.get("/admin/api/auditlog/")
        assert response.status_code == 200
        assert b"testuser" in response.content


# -- Detail/change page tests --


class TestAdminDetailPages:
    """Change/detail pages must load without errors."""

    def test_tenant_change(self, admin_client: Client, sample_tenant: Tenant) -> None:
        response = admin_client.get(f"/admin/api/tenant/{sample_tenant.pk}/change/")
        assert response.status_code == 200

    def test_job_change(self, admin_client: Client, sample_job: Job) -> None:
        response = admin_client.get(f"/admin/api/job/{sample_job.pk}/change/")
        assert response.status_code == 200

    def test_storage_change(
        self, admin_client: Client, sample_storage: StorageConfig
    ) -> None:
        response = admin_client.get(
            f"/admin/api/storageconfig/{sample_storage.pk}/change/"
        )
        assert response.status_code == 200

    def test_auditlog_detail(
        self, admin_client: Client, sample_audit: AuditLog
    ) -> None:
        response = admin_client.get(f"/admin/api/auditlog/{sample_audit.pk}/change/")
        assert response.status_code == 200


# -- Security tests --


class TestAdminSecurity:
    """Admin security: masked secrets, audit immutability."""

    def test_s3_secret_masked(
        self, admin_client: Client, sample_storage: StorageConfig
    ) -> None:
        """S3 secret key must be masked on the change page."""
        response = admin_client.get(
            f"/admin/api/storageconfig/{sample_storage.pk}/change/"
        )
        content = response.content.decode()
        # Full secret must NOT appear
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in content
        # Last 4 chars should be visible
        assert "EKEY" in content

    def test_auditlog_no_add(self, admin_client: Client) -> None:
        """AuditLog must not allow adding entries via admin."""
        response = admin_client.get("/admin/api/auditlog/add/")
        assert response.status_code == 403

    def test_auditlog_no_delete(
        self, admin_client: Client, sample_audit: AuditLog
    ) -> None:
        """AuditLog must not allow deletion via admin."""
        response = admin_client.post(
            f"/admin/api/auditlog/{sample_audit.pk}/delete/",
            {"post": "yes"},
        )
        assert response.status_code == 403

    def test_unauthenticated_no_access(self, db) -> None:
        """Unauthenticated users must not access admin."""
        client = Client()
        response = client.get("/admin/api/tenant/")
        assert response.status_code == 302  # redirect to login


# -- Tenant filter test --


class TestAdminTenantFilter:
    """Jobs and storage configs must be filterable by tenant."""

    def test_job_filter_by_tenant(
        self, admin_client: Client, sample_job: Job, sample_tenant: Tenant
    ) -> None:
        url = f"/admin/api/job/?tenant__id__exact={sample_tenant.pk}"
        response = admin_client.get(url)
        assert response.status_code == 200
        assert b"test.wav" in response.content

    def test_storage_filter_by_tenant(
        self, admin_client: Client, sample_storage: StorageConfig, sample_tenant: Tenant
    ) -> None:
        url = f"/admin/api/storageconfig/?tenant__id__exact={sample_tenant.pk}"
        response = admin_client.get(url)
        assert response.status_code == 200
        assert b"Test S3" in response.content
