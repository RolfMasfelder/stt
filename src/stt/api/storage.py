"""Storage backend abstraction layer (ADR-11).

Defines the StorageBackend protocol and concrete implementations
for storing processing results to configurable destinations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

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
        return LocalFileBackend(
            base_path=config.base_path,
            backend_name=config.name,
        )
    if config.backend_type == StorageBackendType.S3:
        raise StorageError("S3 backend not yet implemented (planned: 2b.3)")

    raise StorageError(f"Unknown backend type: {config.backend_type}")
