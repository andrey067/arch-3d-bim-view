"""Unit tests for detection.py (T023) — magic bytes detection."""
from __future__ import annotations

import pytest

from app.features.models.detection import detect_format, get_extension, is_rejected_format
from app.features.models.models import SourceFormat


class TestDetectFormat:
    def test_detect_glb(self) -> None:
        headers = b"glTF" + b"\x02\x00\x00\x00" + b"\x0c\x00\x00\x00" + b"\x00" * 500
        assert detect_format(headers) == SourceFormat.glb

    def test_detect_ifc(self) -> None:
        headers = b"ISO-10303-21;\nHEADER;\nENDSEC;\n" + b"\x00" * 480
        assert detect_format(headers) == SourceFormat.ifc

    def test_detect_dae(self) -> None:
        headers = b'<?xml version="1.0"?>\n<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema">\n</COLLADA>'
        assert detect_format(headers) == SourceFormat.dae

    def test_detect_obj_with_comment(self) -> None:
        headers = b"# OBJ file\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nf 1 2 3\n"
        assert detect_format(headers) == SourceFormat.obj

    def test_detect_obj_with_vertex(self) -> None:
        headers = b"v 0.0 0.0 0.0\nv 1.0 0.0 0.0\nvn 0.0 0.0 1.0\nf 1//1 2//1 3//1\n"
        assert detect_format(headers) == SourceFormat.obj

    def test_detect_empty_returns_none(self) -> None:
        assert detect_format(b"") is None

    def test_detect_unknown_returns_none(self) -> None:
        headers = b"\x00\x01\x02\x03" * 128
        assert detect_format(headers) is None

    def test_detect_text_file_returns_none(self) -> None:
        headers = b"Hello, World!\nThis is a text file.\n"
        assert detect_format(headers) is None


class TestIsRejectedFormat:
    def test_stl_text_rejected(self) -> None:
        headers = b"solid test\nfacet normal 0 0 0\nendfacet\nendsolid test\n"
        assert is_rejected_format(headers) is True

    def test_dwg_rejected(self) -> None:
        headers = b"AC1032" + b"\x00" * 506
        assert is_rejected_format(headers) is True

    def test_dxf_rejected(self) -> None:
        headers = b"0\r\nSECTION\r\n2\r\nHEADER\r\n"
        assert is_rejected_format(headers) is True

    def test_skp_rejected(self) -> None:
        headers = b"TSFF" + b"\x00" * 508
        assert is_rejected_format(headers) is True

    def test_glb_not_rejected(self) -> None:
        headers = b"glTF" + b"\x00" * 508
        assert is_rejected_format(headers) is False

    def test_ifc_not_rejected(self) -> None:
        headers = b"ISO-10303-21" + b"\x00" * 500
        assert is_rejected_format(headers) is False

    def test_empty_not_rejected(self) -> None:
        assert is_rejected_format(b"") is False


class TestGetExtension:
    def test_simple_extension(self) -> None:
        assert get_extension("model.glb") == "glb"

    def test_multiple_dots(self) -> None:
        assert get_extension("my.model.ifc") == "ifc"

    def test_no_extension(self) -> None:
        assert get_extension("README") is None

    def test_uppercase_extension(self) -> None:
        assert get_extension("model.GLB") == "glb"

    def test_hidden_file_no_extension(self) -> None:
        assert get_extension(".gitignore") == "gitignore"
