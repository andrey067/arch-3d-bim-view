"""LocalDiskStorage — file storage backed by the local filesystem.

Layout follows the monorepo convention::

    storage/
      originals/<project_id>/<file_id>__<name>
      converted/<project_id>/<file_id>.glb
      thumbnails/<project_id>/<file_id>.webp

Keys are **always relative** to the storage root.  Absolute paths
and ``..`` components are rejected to prevent path-traversal.
"""
from __future__ import annotations

import shutil
from io import BufferedReader, FileIO
from pathlib import Path, PurePosixPath
from typing import BinaryIO


class PathTraversalError(ValueError):
    """Raised when a key attempts to escape the storage root."""


def _validate_key(key: str) -> None:
    """Reject absolute paths and ``..`` components."""
    p = PurePosixPath(key)
    if p.is_absolute():
        raise PathTraversalError(f"Absolute key rejected: {key!r}")
    if ".." in p.parts:
        raise PathTraversalError(f"Key contains '..': {key!r}")


class LocalDiskStorage:
    """Implementation of ``ObjectStorage`` backed by a local directory."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # -- internal helpers ---------------------------------------------------

    def _resolve(self, key: str) -> Path:
        _validate_key(key)
        return (self._root / key).resolve()

    # -- public API ---------------------------------------------------------

    def put(self, key: str, src: Path | BinaryIO, content_type: str = "application/octet-stream") -> str:
        """Write *src* to *key*, creating parent dirs as needed."""
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, (Path, str)):
            shutil.copy2(str(src), dest)
        else:
            with open(dest, "wb") as dst_file:
                shutil.copyfileobj(src, dst_file)  # type: ignore[arg-type]
        return key

    def get(self, key: str) -> BinaryIO:
        path = self._resolve(key)
        return FileIO(path, mode="rb")  # type: ignore[return-value]

    def open_for_read(self, key: str) -> BinaryIO:
        path = self._resolve(key)
        return BufferedReader(open(path, "rb"))  # type: ignore[arg-type]

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def get_size(self, key: str) -> int:
        return self._resolve(key).stat().st_size

    def can_write(self) -> bool:
        try:
            probe = self._root / ".write_probe"
            probe.write_text("ok")
            probe.unlink()
            return True
        except OSError:
            return False
