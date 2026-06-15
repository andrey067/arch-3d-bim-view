"""Storage primitives — Protocol and implementations."""
from app.core.storage.base import ObjectStorage
from app.core.storage.local_disk import LocalDiskStorage

__all__ = ["ObjectStorage", "LocalDiskStorage"]
