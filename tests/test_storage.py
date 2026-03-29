"""Tests for storage backend abstraction (ADR-11)."""

from unittest.mock import MagicMock, patch

import pytest

from stt.api.storage import (
    EncryptingBackend,
    LocalFileBackend,
    S3Backend,
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

    def test_s3_backend(self) -> None:
        from stt.api.models import StorageBackendType, StorageConfig

        with patch("stt.api.storage.boto3") as mock_boto:
            config = StorageConfig.objects.create(
                name="test-s3",
                backend_type=StorageBackendType.S3,
                s3_endpoint_url="https://s3.example.com",
                s3_bucket="test-bucket",
                s3_access_key="AKIATEST",
                s3_secret_key="secret",
                s3_region="eu-central-1",
            )
            backend = get_backend(config)
            assert isinstance(backend, S3Backend)
            assert backend.name == "test-s3"
            mock_boto.client.assert_called_once()

    def test_unknown_backend_raises(self, tmp_path) -> None:
        config = MagicMock()
        config.backend_type = "unknown"
        config.name = "bad"
        with pytest.raises(StorageError, match="Unknown backend"):
            get_backend(config)


class TestS3Backend:
    """Unit tests for S3Backend with mocked boto3 client."""

    @pytest.fixture
    def mock_client(self):
        with patch("stt.api.storage.boto3") as mock_boto:
            client = MagicMock()
            mock_boto.client.return_value = client
            yield client

    @pytest.fixture
    def backend(self, mock_client) -> S3Backend:
        return S3Backend(
            endpoint_url="https://s3.example.com",
            bucket="test-bucket",
            access_key="AKIATEST",
            secret_key="secret",
            region="eu-central-1",
            backend_name="test-s3",
        )

    def test_implements_protocol(self, backend: S3Backend) -> None:
        assert isinstance(backend, StorageBackend)

    def test_name(self, backend: S3Backend) -> None:
        assert backend.name == "test-s3"

    def test_store(self, backend: S3Backend, mock_client: MagicMock) -> None:
        result = backend.store(b"hello", "test.txt")
        assert result.backend_name == "test-s3"
        assert result.path == "s3://test-bucket/test.txt"
        assert result.size_bytes == 5
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt", Body=b"hello"
        )

    def test_store_with_sub_path(
        self, backend: S3Backend, mock_client: MagicMock
    ) -> None:
        result = backend.store(b"data", "file.txt", sub_path="output")
        assert result.path == "s3://test-bucket/output/file.txt"
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="output/file.txt", Body=b"data"
        )

    def test_store_error(self, backend: S3Backend, mock_client: MagicMock) -> None:
        mock_client.put_object.side_effect = Exception("network error")
        with pytest.raises(StorageError, match="put_object failed"):
            backend.store(b"data", "test.txt")

    def test_retrieve(self, backend: S3Backend, mock_client: MagicMock) -> None:
        body = MagicMock()
        body.read.return_value = b"content"
        mock_client.get_object.return_value = {"Body": body}
        data = backend.retrieve("test.txt")
        assert data == b"content"
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )

    def test_retrieve_not_found(
        self, backend: S3Backend, mock_client: MagicMock
    ) -> None:
        mock_client.exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})
        mock_client.get_object.side_effect = mock_client.exceptions.NoSuchKey()
        with pytest.raises(StorageError, match="not found"):
            backend.retrieve("missing.txt")

    def test_delete(self, backend: S3Backend, mock_client: MagicMock) -> None:
        backend.delete("test.txt")
        mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )

    def test_delete_error(self, backend: S3Backend, mock_client: MagicMock) -> None:
        mock_client.delete_object.side_effect = Exception("denied")
        with pytest.raises(StorageError, match="delete_object failed"):
            backend.delete("test.txt")

    def test_exists_true(self, backend: S3Backend, mock_client: MagicMock) -> None:
        assert backend.exists("test.txt") is True
        mock_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="test.txt"
        )

    def test_exists_false(self, backend: S3Backend, mock_client: MagicMock) -> None:
        error_response = {"Error": {"Code": "404"}}
        mock_client.exceptions.ClientError = type("ClientError", (Exception,), {})
        exc = mock_client.exceptions.ClientError()
        exc.response = error_response
        mock_client.head_object.side_effect = exc
        assert backend.exists("missing.txt") is False

    def test_path_traversal_blocked(self, backend: S3Backend) -> None:
        with pytest.raises(StorageError, match="traversal"):
            backend.store(b"data", "../../../etc/passwd")

    def test_path_traversal_in_sub_path_blocked(self, backend: S3Backend) -> None:
        with pytest.raises(StorageError, match="traversal"):
            backend.retrieve("file.txt", sub_path="../../etc")

    def test_test_connection_success(
        self, backend: S3Backend, mock_client: MagicMock
    ) -> None:
        body = MagicMock()
        body.read.return_value = b"STT storage test"
        mock_client.get_object.return_value = {"Body": body}
        result = backend.test_connection()
        assert result.success is True
        assert result.connection is True
        assert result.write is True
        assert result.read is True
        assert result.delete is True
        assert result.duration_ms >= 0

    def test_test_connection_bucket_not_found(
        self, backend: S3Backend, mock_client: MagicMock
    ) -> None:
        mock_client.head_bucket.side_effect = Exception("NoSuchBucket")
        result = backend.test_connection()
        assert result.success is False
        assert result.connection is False


class TestEncryptingBackend:
    """Unit tests for EncryptingBackend AES-256-GCM wrapper (ADR-08)."""

    TEST_KEY_HEX = "a" * 64

    @pytest.fixture
    def inner(self, tmp_path) -> LocalFileBackend:
        return LocalFileBackend(str(tmp_path))

    @pytest.fixture
    def backend(self, inner: LocalFileBackend) -> EncryptingBackend:
        return EncryptingBackend(inner, self.TEST_KEY_HEX)

    def test_implements_protocol(self, backend: EncryptingBackend) -> None:
        assert isinstance(backend, StorageBackend)

    def test_name_delegated(self, backend: EncryptingBackend) -> None:
        assert backend.name == "local"

    def test_roundtrip(self, backend: EncryptingBackend) -> None:
        plaintext = b"Hello, encrypted world!"
        backend.store(plaintext, "test.txt")
        result = backend.retrieve("test.txt")
        assert result == plaintext

    def test_stored_data_is_encrypted(
        self, backend: EncryptingBackend, inner: LocalFileBackend
    ) -> None:
        plaintext = b"sensitive data"
        backend.store(plaintext, "secret.txt")
        raw = inner.retrieve("secret.txt")
        assert raw != plaintext
        assert len(raw) > len(plaintext)

    def test_delete_delegated(
        self, backend: EncryptingBackend, inner: LocalFileBackend
    ) -> None:
        backend.store(b"data", "del.txt")
        assert inner.exists("del.txt")
        backend.delete("del.txt")
        assert not inner.exists("del.txt")

    def test_exists_delegated(self, backend: EncryptingBackend) -> None:
        assert not backend.exists("nope.txt")
        backend.store(b"x", "nope.txt")
        assert backend.exists("nope.txt")

    def test_test_connection_delegated(self, backend: EncryptingBackend) -> None:
        result = backend.test_connection()
        assert result.success is True

    def test_wrong_key_fails_decrypt(self, backend: EncryptingBackend) -> None:
        backend.store(b"secret", "file.txt")
        wrong_key = "b" * 64
        bad_backend = EncryptingBackend(backend._inner, wrong_key)
        with pytest.raises(StorageError, match="Decryption failed"):
            bad_backend.retrieve("file.txt")

    def test_empty_key_raises(self, inner: LocalFileBackend) -> None:
        with pytest.raises(StorageError, match="not set"):
            EncryptingBackend(inner, "")

    def test_short_key_raises(self, inner: LocalFileBackend) -> None:
        with pytest.raises(StorageError, match="32 bytes"):
            EncryptingBackend(inner, "aa" * 16)

    def test_invalid_hex_raises(self, inner: LocalFileBackend) -> None:
        with pytest.raises(StorageError, match="hex"):
            EncryptingBackend(inner, "not-valid-hex")

    def test_truncated_data_raises(self, backend: EncryptingBackend) -> None:
        backend.store(b"data", "tampered.txt")
        backend._inner.store(b"short", "tampered.txt")
        with pytest.raises(StorageError, match="too short"):
            backend.retrieve("tampered.txt")


@pytest.mark.django_db
class TestGetBackendEncryption:
    """Test that get_backend wraps with EncryptingBackend when encrypt_at_rest=True."""

    TEST_KEY_HEX = "a" * 64

    def test_local_without_encryption(self, tmp_path) -> None:
        from stt.api.models import StorageBackendType, StorageConfig

        config = StorageConfig.objects.create(
            name="plain",
            backend_type=StorageBackendType.LOCAL,
            base_path=str(tmp_path),
            encrypt_at_rest=False,
        )
        backend = get_backend(config)
        assert isinstance(backend, LocalFileBackend)
        assert not isinstance(backend, EncryptingBackend)

    def test_local_with_encryption(self, tmp_path, settings) -> None:
        from stt.api.models import StorageBackendType, StorageConfig

        settings.STORAGE_ENCRYPTION_KEY = self.TEST_KEY_HEX
        config = StorageConfig.objects.create(
            name="encrypted",
            backend_type=StorageBackendType.LOCAL,
            base_path=str(tmp_path),
            encrypt_at_rest=True,
        )
        backend = get_backend(config)
        assert isinstance(backend, EncryptingBackend)

    def test_encryption_no_key_raises(self, tmp_path, settings) -> None:
        from stt.api.models import StorageBackendType, StorageConfig

        settings.STORAGE_ENCRYPTION_KEY = ""
        config = StorageConfig.objects.create(
            name="no-key",
            backend_type=StorageBackendType.LOCAL,
            base_path=str(tmp_path),
            encrypt_at_rest=True,
        )
        with pytest.raises(StorageError, match="not set"):
            get_backend(config)
