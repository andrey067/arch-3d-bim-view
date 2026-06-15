"""ObjectStorage Protocol — abstraction for file storage backends.

Sprint 0 ships `LocalDiskStorage` (T028). Swapping to S3/MinIO in
the future means adding a new implementation + configuring DI;
no call-site changes.
"""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Protocol, runtime_checkable


@runtime_checkable
class ObjectStorage(Protocol):
    """Storage backend contract. Keys are always relative to root."""

    def put(self, key: str, src: Path | BinaryIO, content_type: str) -> str:
        """Store *src* under *key*. Returns the storage key used."""
        ...

    def get(self, key: str) -> BinaryIO:
        """Return an open binary file-like object for reading."""
        ...

    def open_for_read(self, key: str) -> BinaryIO:
        """Streaming read (same as get; explicit name for clarity)."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object at *key*. No-op if absent."""
        ...

    def exists(self, key: str) -> bool:
        """Return True if an object is stored at *key*."""
        ...

    def get_size(self, key: str) -> int:
        """Return the size in bytes of the object at *key*."""
        ...

    def can_write(self) -> bool:
        """Probe write access to the storage root."""
        ...
