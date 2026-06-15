"""Unit tests for core/storage — LocalDiskStorage and key builders.

Covers:
- LocalDiskStorage: put, get, exists, delete, open_for_read, get_size, can_write
- Path-traversal prevention
- Storage key builders: original_key, glb_key, usdz_key, qr_key
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.core.storage.keys import glb_key, original_key, usdz_key, qr_key
from app.core.storage.local_disk import LocalDiskStorage, PathTraversalError


class TestLocalDiskStoragePut:
    def test_put_from_path(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "source.bin"
        src.write_bytes(b"hello world")

        key = storage.put("a/b/test.bin", src, content_type="application/octet-stream")

        assert key == "a/b/test.bin"
        assert (tmp_path / "store" / "a" / "b" / "test.bin").exists()
        assert (tmp_path / "store" / "a" / "b" / "test.bin").read_bytes() == b"hello world"

    def test_put_from_bytes_io(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        data = io.BytesIO(b"streamed content")

        storage.put("file.txt", data, content_type="text/plain")

        assert (tmp_path / "store" / "file.txt").read_bytes() == b"streamed content"

    def test_put_creates_parent_dirs(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"data")

        storage.put("deep/nested/dir/file.bin", src, content_type="application/octet-stream")

        assert (tmp_path / "store" / "deep" / "nested" / "dir" / "file.bin").exists()

    def test_put_overwrites_existing(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src1 = tmp_path / "src1.bin"
        src1.write_bytes(b"old")
        src2 = tmp_path / "src2.bin"
        src2.write_bytes(b"new")

        storage.put("file.bin", src1, content_type="application/octet-stream")
        storage.put("file.bin", src2, content_type="application/octet-stream")

        assert (tmp_path / "store" / "file.bin").read_bytes() == b"new"


class TestLocalDiskStorageGet:
    def test_get_returns_readable_stream(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"stored data")
        storage.put("file.bin", src, content_type="application/octet-stream")

        stream = storage.get("file.bin")
        assert stream.read() == b"stored data"

    def test_get_nonexistent_raises(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")

        with pytest.raises(FileNotFoundError):
            storage.get("nonexistent.bin")


class TestLocalDiskStorageExists:
    def test_exists_returns_true_for_stored_file(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"data")
        storage.put("file.bin", src, content_type="application/octet-stream")

        assert storage.exists("file.bin") is True

    def test_exists_returns_false_for_missing(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")

        assert storage.exists("missing.bin") is False


class TestLocalDiskStorageDelete:
    def test_delete_removes_file(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"data")
        storage.put("file.bin", src, content_type="application/octet-stream")

        storage.delete("file.bin")

        assert storage.exists("file.bin") is False

    def test_delete_nonexistent_is_noop(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        storage.delete("nonexistent.bin")


class TestLocalDiskStorageGetSize:
    def test_get_size_returns_byte_count(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"12345")
        storage.put("file.bin", src, content_type="application/octet-stream")

        assert storage.get_size("file.bin") == 5

    def test_get_size_nonexistent_raises(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")

        with pytest.raises(FileNotFoundError):
            storage.get_size("missing.bin")


class TestLocalDiskStorageOpenForRead:
    def test_open_for_read_returns_stream(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"readable")
        storage.put("file.bin", src, content_type="application/octet-stream")

        stream = storage.open_for_read("file.bin")
        assert stream.read() == b"readable"


class TestLocalDiskStorageCanWrite:
    def test_can_write_returns_true(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        assert storage.can_write() is True


class TestPathTraversalPrevention:
    def test_rejects_absolute_key(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"evil")

        with pytest.raises(PathTraversalError, match="Absolute key rejected"):
            storage.put("/etc/passwd", src, content_type="application/octet-stream")

    def test_rejects_dotdot_key(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"evil")

        with pytest.raises(PathTraversalError, match="contains '\\.\\.'"):
            storage.put("../etc/passwd", src, content_type="application/octet-stream")

    def test_rejects_dotdot_in_middle(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")
        src = tmp_path / "src.bin"
        src.write_bytes(b"evil")

        with pytest.raises(PathTraversalError):
            storage.put("a/../../../etc/passwd", src, content_type="application/octet-stream")

    def test_rejects_dotdot_on_get(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")

        with pytest.raises(PathTraversalError):
            storage.get("../etc/passwd")

    def test_rejects_dotdot_on_exists(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")

        with pytest.raises(PathTraversalError):
            storage.exists("../etc/passwd")

    def test_rejects_dotdot_on_delete(self, tmp_path: Path) -> None:
        storage = LocalDiskStorage(tmp_path / "store")

        with pytest.raises(PathTraversalError):
            storage.delete("../etc/passwd")


class TestOriginalKey:
    def test_basic_key(self) -> None:
        key = original_key("proj-1", "file-1", "model.ifc")
        assert key == "originals/proj-1/file-1__model.ifc"

    def test_sanitizes_path_separators(self) -> None:
        key = original_key("proj", "file", "path/to/model.ifc")
        assert key == "originals/proj/file__path_to_model.ifc"
        assert ".." not in key

    def test_sanitizes_backslashes(self) -> None:
        key = original_key("proj", "file", "path\\to\\model.ifc")
        assert key == "originals/proj/file__path_to_model.ifc"

    def test_sanitizes_null_bytes(self) -> None:
        key = original_key("proj", "file", "model\x00.ifc")
        assert "\x00" not in key

    def test_truncates_long_filename(self) -> None:
        long_name = "a" * 300 + ".ifc"
        key = original_key("proj", "file", long_name)
        name_part = key.split("__", 1)[1]
        assert len(name_part) <= 255


class TestGlbKey:
    def test_basic_key(self) -> None:
        key = glb_key("proj-1", "file-1")
        assert key == "converted/proj-1/file-1.glb"

    def test_always_relative(self) -> None:
        key = glb_key("proj", "file")
        assert not key.startswith("/")


class TestUsdzKey:
    def test_basic_key(self) -> None:
        key = usdz_key("proj-1", "file-1")
        assert key == "usdz/proj-1/file-1.usdz"

    def test_always_relative(self) -> None:
        key = usdz_key("proj", "file")
        assert not key.startswith("/")


class TestQrKey:
    def test_basic_key(self) -> None:
        key = qr_key("proj-1", "file-1")
        assert key == "qr/proj-1/file-1.png"

    def test_always_relative(self) -> None:
        key = qr_key("proj", "file")
        assert not key.startswith("/")
