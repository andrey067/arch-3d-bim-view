"""Magic bytes detection for 3D file formats.

Identifies source_format from the first bytes of a file stream.
Returns a SourceFormat enum or None if the format is not recognized.

Supported formats (MVP):
- IFC: starts with `ISO-10303-21`
- DAE (COLLADA): XML with `<COLLADA` within first 256 bytes
- OBJ: starts with `#` or `v` (vertex)
- GLB: starts with `glTF` magic (0x67, 0x6C, 0x54, 0x46)

Rejected formats (HTTP 415):
- STL, RVT, DWG, DXF, SKP
"""
from __future__ import annotations

from app.features.models.models import SourceFormat

# Magic byte signatures
_GLB_MAGIC = b"glTF"
_IFC_MAGIC = b"ISO-10303-21"
_DAE_MARKER = b"COLLADA"

# Rejected format signatures
_STL_BINARY_MAGIC = b"solid"  # text STL starts with "solid"
_STL_BINARY_CHECK = b"\x80"  # binary STL has specific header


def detect_format(headers: bytes) -> SourceFormat | None:
    """Detect the source format from the first bytes of a file.

    Args:
        headers: The first 512+ bytes of the file.

    Returns:
        SourceFormat enum if recognized, None otherwise.
    """
    if not headers:
        return None

    # GLB: magic bytes "glTF" at offset 0
    if headers[:4] == _GLB_MAGIC:
        return SourceFormat.glb

    # IFC: starts with "ISO-10303-21"
    if headers[:len(_IFC_MAGIC)] == _IFC_MAGIC:
        return SourceFormat.ifc

    # DAE: XML file with COLLADA marker
    try:
        head_text = headers[:512].decode("utf-8", errors="ignore")
        if "<COLLADA" in head_text:
            return SourceFormat.dae
    except Exception:
        pass

    # OBJ: starts with comment (#) or vertex (v ) or other OBJ markers
    first_two = headers[:2]
    if first_two in (b"# ", b"v "):
        return SourceFormat.obj
    # Also check for OBJ files starting with other markers
    try:
        head_text = headers[:512].decode("utf-8", errors="ignore")
        lines = head_text.split("\n")[:10]
        for line in lines:
            stripped = line.strip()
            if stripped and (
                stripped.startswith("vn ")
                or stripped.startswith("vt ")
                or stripped.startswith("f ")
                or stripped.startswith("o ")
                or stripped.startswith("g ")
                or stripped.startswith("mtllib ")
                or stripped.startswith("usemtl ")
            ):
                return SourceFormat.obj
    except Exception:
        pass

    return None


def is_rejected_format(headers: bytes) -> bool:
    """Check if the file is a format explicitly rejected by the MVP.

    Returns True for STL, RVT, DWG, DXF, SKP.
    """
    if not headers:
        return False

    # STL detection
    if headers[:5] == b"solid":
        # Could be text STL - check if it has "facet" in the header
        try:
            head = headers[:256].decode("utf-8", errors="ignore")
            if "facet" in head.lower():
                return True
        except Exception:
            pass

    # DWG: starts with "AC10" followed by version
    if headers[:4] == b"AC10":
        return True

    # DXF: starts with "0\r\nSECTION" or "0\nSECTION"
    if headers[:10].startswith(b"0\r\nSECTION") or headers[:10].startswith(b"0\nSECTION"):
        return True

    # SKP: starts with specific magic
    if headers[:4] == b"TSFF":
        return True

    # RVT: starts with specific magic (Autodesk Revit)
    if headers[:4] == b"\x00\x00\x00\x18" and len(headers) > 8:
        # RVT files have a specific header pattern
        if headers[4:8] == b"\x00\x00\x00\x00":
            return True

    return False


def get_extension(filename: str) -> str | None:
    """Extract file extension (lowercase, without dot)."""
    if "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()
