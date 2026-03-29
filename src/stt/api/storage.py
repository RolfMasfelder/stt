"""Storage backend abstraction layer (ADR-11).

Defines the StorageBackend protocol and concrete implementations
for storing processing results to configurable destinations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import boto3
from botocore.config import Config as BotoConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StorageResult:
    """Result of a storage operation."""

    backend_name: str
    path: str
    size_bytes: int


@dataclass(frozen=True)
class StorageTestResult:
    """Result of a storage backend connectivity test."""

    connection: bool
    write: bool
    read: bool
    delete: bool
    message: str
    duration_ms: int

    @property
    def success(self) -> bool:
        return self.connection and self.write and self.read and self.delete


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol defining the storage backend interface."""

    @property
    def name(self) -> str:
        """Human-readable name of this backend instance."""
        ...

    def store(self, content: bytes, filename: str, sub_path: str = "") -> StorageResult:
        """Store content to the backend.

        Args:
            content: The file content as bytes.
            filename: Target filename.
            sub_path: Optional subdirectory within the backend's base path.

        Returns:
            StorageResult with the storage location details.

        Raises:
            StorageError: If the storage operation fails.
        """
        ...

    def retrieve(self, filename: str, sub_path: str = "") -> bytes:
        """Retrieve content from the backend.

        Args:
            filename: The filename to retrieve.
            sub_path: Optional subdirectory within the backend's base path.

        Returns:
            The file content as bytes.

        Raises:
            StorageError: If the file is not found or retrieval fails.
        """
        ...

    def delete(self, filename: str, sub_path: str = "") -> None:
        """Delete a file from the backend.

        Args:
            filename: The filename to delete.
            sub_path: Optional subdirectory within the backend's base path.

        Raises:
            StorageError: If the deletion fails.
        """
        ...

    def exists(self, filename: str, sub_path: str = "") -> bool:
        """Check if a file exists in the backend.

        Args:
            filename: The filename to check.
            sub_path: Optional subdirectory within the backend's base path.

        Returns:
            True if the file exists.
        """
        ...

    def test_connection(self) -> StorageTestResult:
        """Test the backend connection with write/read/delete operations.

        Returns:
            StorageTestResult with detailed check results.
        """
        ...


class StorageError(Exception):
    """Raised when a storage operation fails."""


class LocalFileBackend:
    """Storage backend for the local filesystem (ADR-11)."""

    def __init__(self, base_path: str, backend_name: str = "local") -> None:
        self._base_path = Path(base_path)
        self._name = backend_name

    @property
    def name(self) -> str:
        return self._name

    def _resolve(self, filename: str, sub_path: str = "") -> Path:
        """Resolve a filename to an absolute path, preventing path traversal."""
        if sub_path:
            target = self._base_path / sub_path / filename
        else:
            target = self._base_path / filename

        # Prevent path traversal attacks
        resolved = target.resolve()
        base_resolved = self._base_path.resolve()
        if not str(resolved).startswith(str(base_resolved)):
            raise StorageError(f"Path traversal detected: {filename}")

        return resolved

    def store(self, content: bytes, filename: str, sub_path: str = "") -> StorageResult:
        target = self._resolve(filename, sub_path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            logger.info("Stored %d bytes to %s", len(content), target)
            return StorageResult(
                backend_name=self._name,
                path=str(target),
                size_bytes=len(content),
            )
        except OSError as e:
            raise StorageError(f"Failed to write {target}: {e}") from e

    def retrieve(self, filename: str, sub_path: str = "") -> bytes:
        target = self._resolve(filename, sub_path)
        if not target.exists():
            raise StorageError(f"File not found: {target}")
        try:
            return target.read_bytes()
        except OSError as e:
            raise StorageError(f"Failed to read {target}: {e}") from e

    def delete(self, filename: str, sub_path: str = "") -> None:
        target = self._resolve(filename, sub_path)
        if not target.exists():
            return  # Idempotent delete
        try:
            target.unlink()
            logger.info("Deleted %s", target)
        except OSError as e:
            raise StorageError(f"Failed to delete {target}: {e}") from e

    def exists(self, filename: str, sub_path: str = "") -> bool:
        target = self._resolve(filename, sub_path)
        return target.exists()

    def test_connection(self) -> StorageTestResult:
        import time

        start = time.monotonic()
        checks = {"connection": False, "write": False, "read": False, "delete": False}
        test_file = "_stt_storage_test.tmp"
        test_content = b"STT storage test"

        try:
            # Connection: check base path exists or can be created
            self._base_path.mkdir(parents=True, exist_ok=True)
            checks["connection"] = True

            # Write
            target = self._base_path / test_file
            target.write_bytes(test_content)
            checks["write"] = True

            # Read
            data = target.read_bytes()
            checks["read"] = data == test_content

            # Delete
            target.unlink()
            checks["delete"] = True

            message = "Alle Prüfungen erfolgreich"
        except OSError as e:
            message = str(e)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return StorageTestResult(
            connection=checks["connection"],
            write=checks["write"],
            read=checks["read"],
            delete=checks["delete"],
            message=message,
            duration_ms=elapsed_ms,
        )


class S3Backend:
    """Storage backend for S3-compatible object storage (ADR-11)."""

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "",
        backend_name: str = "s3",
    ) -> None:
        self._bucket = bucket
        self._name = backend_name

        client_kwargs: dict[str, str | BotoConfig] = {}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if region:
            client_kwargs["region_name"] = region

        self._client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
            **client_kwargs,
        )

    @property
    def name(self) -> str:
        return self._name

    def _key(self, filename: str, sub_path: str = "") -> str:
        """Build an S3 object key, preventing path traversal."""
        from pathlib import PurePosixPath

        parts = (
            PurePosixPath(sub_path) / filename if sub_path else PurePosixPath(filename)
        )
        # Normalise and reject traversal
        normalised = PurePosixPath(*parts.parts)
        if ".." in normalised.parts:
            raise StorageError(f"Path traversal detected: {filename}")
        return str(normalised)

    def store(self, content: bytes, filename: str, sub_path: str = "") -> StorageResult:
        key = self._key(filename, sub_path)
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
            logger.info(
                "Stored %d bytes to s3://%s/%s", len(content), self._bucket, key
            )
            return StorageResult(
                backend_name=self._name,
                path=f"s3://{self._bucket}/{key}",
                size_bytes=len(content),
            )
        except Exception as e:
            raise StorageError(f"S3 put_object failed for {key}: {e}") from e

    def retrieve(self, filename: str, sub_path: str = "") -> bytes:
        key = self._key(filename, sub_path)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except self._client.exceptions.NoSuchKey as e:
            raise StorageError(f"File not found: s3://{self._bucket}/{key}") from e
        except Exception as e:
            raise StorageError(f"S3 get_object failed for {key}: {e}") from e

    def delete(self, filename: str, sub_path: str = "") -> None:
        key = self._key(filename, sub_path)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("Deleted s3://%s/%s", self._bucket, key)
        except Exception as e:
            raise StorageError(f"S3 delete_object failed for {key}: {e}") from e

    def exists(self, filename: str, sub_path: str = "") -> bool:
        key = self._key(filename, sub_path)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise StorageError(f"S3 head_object failed for {key}: {e}") from e
        except Exception as e:
            raise StorageError(f"S3 head_object failed for {key}: {e}") from e

    def test_connection(self) -> StorageTestResult:
        import time

        start = time.monotonic()
        checks = {"connection": False, "write": False, "read": False, "delete": False}
        test_key = "_stt_storage_test.tmp"
        test_content = b"STT storage test"

        try:
            # Connection: verify bucket accessibility
            self._client.head_bucket(Bucket=self._bucket)
            checks["connection"] = True

            # Write
            self._client.put_object(
                Bucket=self._bucket, Key=test_key, Body=test_content
            )
            checks["write"] = True

            # Read
            resp = self._client.get_object(Bucket=self._bucket, Key=test_key)
            data = resp["Body"].read()
            checks["read"] = data == test_content

            # Delete
            self._client.delete_object(Bucket=self._bucket, Key=test_key)
            checks["delete"] = True

            message = "Alle Prüfungen erfolgreich"
        except Exception as e:
            message = str(e)

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return StorageTestResult(
            connection=checks["connection"],
            write=checks["write"],
            read=checks["read"],
            delete=checks["delete"],
            message=message,
            duration_ms=elapsed_ms,
        )


class EncryptingBackend:
    """Decorator that adds AES-256-GCM encryption to any StorageBackend (ADR-08).

    Encrypts content before storing and decrypts after retrieval.
    Format: 12-byte nonce + 16-byte tag + ciphertext.
    """

    NONCE_SIZE = 12
    TAG_SIZE = 16

    def __init__(self, inner: StorageBackend, key_hex: str) -> None:
        if not key_hex:
            raise StorageError(
                "STORAGE_ENCRYPTION_KEY not set — required when encrypt_at_rest=True"
            )
        try:
            self._key = bytes.fromhex(key_hex)
        except ValueError as e:
            raise StorageError(
                f"Invalid STORAGE_ENCRYPTION_KEY (must be hex): {e}"
            ) from e
        if len(self._key) != 32:
            raise StorageError(
                f"STORAGE_ENCRYPTION_KEY must be 32 bytes (64 hex chars), got {len(self._key)}"
            )
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    def _encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt with AES-256-GCM. Returns nonce + tag + ciphertext."""
        import os

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(self.NONCE_SIZE)
        aesgcm = AESGCM(self._key)
        ct = aesgcm.encrypt(nonce, plaintext, None)
        # ct already includes the 16-byte tag appended by cryptography
        return nonce + ct

    def _decrypt(self, data: bytes) -> bytes:
        """Decrypt AES-256-GCM payload (nonce + tag + ciphertext)."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if len(data) < self.NONCE_SIZE + self.TAG_SIZE:
            raise StorageError("Encrypted data too short")
        nonce = data[: self.NONCE_SIZE]
        ct = data[self.NONCE_SIZE :]
        aesgcm = AESGCM(self._key)
        try:
            return aesgcm.decrypt(nonce, ct, None)
        except Exception as e:
            raise StorageError(f"Decryption failed: {e}") from e

    def store(self, content: bytes, filename: str, sub_path: str = "") -> StorageResult:
        encrypted = self._encrypt(content)
        result = self._inner.store(encrypted, filename, sub_path)
        logger.info("Stored encrypted (%d -> %d bytes)", len(content), len(encrypted))
        return result

    def retrieve(self, filename: str, sub_path: str = "") -> bytes:
        encrypted = self._inner.retrieve(filename, sub_path)
        return self._decrypt(encrypted)

    def delete(self, filename: str, sub_path: str = "") -> None:
        self._inner.delete(filename, sub_path)

    def exists(self, filename: str, sub_path: str = "") -> bool:
        return self._inner.exists(filename, sub_path)

    def test_connection(self) -> StorageTestResult:
        return self._inner.test_connection()


def get_backend(config: object) -> StorageBackend:
    """Create a StorageBackend instance from a StorageConfig model.

    Args:
        config: A StorageConfig model instance.

    Returns:
        A configured StorageBackend implementation.

    Raises:
        StorageError: If the backend type is not supported.
    """
    from .models import StorageBackendType

    if config.backend_type == StorageBackendType.LOCAL:
        backend = LocalFileBackend(
            base_path=config.base_path,
            backend_name=config.name,
        )
    elif config.backend_type == StorageBackendType.S3:
        backend = S3Backend(
            endpoint_url=config.s3_endpoint_url or "",
            bucket=config.s3_bucket or "",
            access_key=config.s3_access_key or "",
            secret_key=config.s3_secret_key or "",
            region=config.s3_region or "",
            backend_name=config.name,
        )
    else:
        raise StorageError(f"Unknown backend type: {config.backend_type}")

    # Wrap with encryption if enabled (ADR-08)
    if getattr(config, "encrypt_at_rest", False):
        from django.conf import settings

        backend = EncryptingBackend(backend, settings.STORAGE_ENCRYPTION_KEY)

    return backend
