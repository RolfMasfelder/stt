"""Tests for storage backend abstraction (ADR-11)."""

import pytest

from stt.api.storage import (
    LocalFileBackend,
    StorageBackend,
    StorageError,
    StorageResult,
    StorageTestResult,
    get_backend,
)


class TestStorageResult:
    def test_fields(self) -> None:
        r = StorageResult(backend_name="local", path="/tmp/test.txt", size_bytes=42)
        assert r.backend_name == "local"
        assert r.path == "/tmp/test.txt"
        assert r.size_bytes == 42


class TestStorageTestResult:
    def test_success_all_true(self) -> None:
        r = StorageTestResult(
            connection=True,
            write=True,
            read=True,
            delete=True,
            message="ok",
            duration_ms=10,
        )
        assert r.success is True

    def test_success_false_if_any_fails(self) -> None:
        r = StorageTestResult(
            connection=True,
            write=True,
            read=False,
            delete=True,
            message="read failed",
            duration_ms=5,
        )
        assert r.success is False


class TestLocalFileBackend:
    def test_implements_protocol(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        assert isinstance(backend, StorageBackend)

    def test_name_default(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        assert backend.name == "local"

    def test_name_custom(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path), backend_name="archive")
        assert backend.name == "archive"

    def test_store_and_retrieve(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        result = backend.store(b"hello world", "test.txt")
        assert result.size_bytes == 11
        assert result.backend_name == "local"

        data = backend.retrieve("test.txt")
        assert data == b"hello world"

    def test_store_with_sub_path(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        backend.store(b"data", "file.txt", sub_path="sub/dir")
        assert (tmp_path / "sub" / "dir" / "file.txt").read_bytes() == b"data"

    def test_retrieve_nonexistent_raises(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        with pytest.raises(StorageError, match="not found"):
            backend.retrieve("missing.txt")

    def test_exists(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        assert backend.exists("test.txt") is False
        backend.store(b"x", "test.txt")
        assert backend.exists("test.txt") is True

    def test_delete(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        backend.store(b"data", "test.txt")
        assert backend.exists("test.txt") is True
        backend.delete("test.txt")
        assert backend.exists("test.txt") is False

    def test_delete_idempotent(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        backend.delete("nonexistent.txt")  # Should not raise

    def test_path_traversal_blocked(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        with pytest.raises(StorageError, match="traversal"):
            backend.store(b"evil", "../../etc/passwd")

    def test_path_traversal_in_sub_path_blocked(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        with pytest.raises(StorageError, match="traversal"):
            backend.retrieve("file.txt", sub_path="../../etc")

    def test_test_connection(self, tmp_path) -> None:
        backend = LocalFileBackend(str(tmp_path))
        result = backend.test_connection()
        assert result.success is True
        assert result.connection is True
        assert result.write is True
        assert result.read is True
        assert result.delete is True
        assert result.duration_ms >= 0

    def test_test_connection_readonly_dir(self, tmp_path) -> None:
        readonly = tmp_path / "readonly"
        readonly.mkdir()
        readonly.chmod(0o444)
        backend = LocalFileBackend(str(readonly))
        result = backend.test_connection()
        assert result.write is False
        # Restore permissions for cleanup
        readonly.chmod(0o755)


@pytest.mark.django_db
class TestGetBackend:
    def test_local_backend(self, tmp_path) -> None:
        from stt.api.models import StorageBackendType, StorageConfig

        config = StorageConfig.objects.create(
            name="test-local",
            backend_type=StorageBackendType.LOCAL,
            base_path=str(tmp_path),
        )
        backend = get_backend(config)
        assert isinstance(backend, LocalFileBackend)
        assert backend.name == "test-local"

    def test_s3_backend_not_yet_implemented(self) -> None:
        from stt.api.models import StorageBackendType, StorageConfig

        config = StorageConfig.objects.create(
            name="test-s3",
            backend_type=StorageBackendType.S3,
            s3_bucket="test",
        )
        with pytest.raises(StorageError, match="not yet implemented"):
            get_backend(config)

    def test_unknown_backend_raises(self, tmp_path) -> None:
        from unittest.mock import MagicMock

        config = MagicMock()
        config.backend_type = "unknown"
        config.name = "bad"
        with pytest.raises(StorageError, match="Unknown backend"):
            get_backend(config)
