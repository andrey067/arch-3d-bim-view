"""Common conversion utilities and error types."""
from __future__ import annotations

from pathlib import Path


class ConversionError(Exception):
    """Raised when a conversion pipeline fails."""

    def __init__(self, message: str, *, stage: str = "unknown") -> None:
        super().__init__(message)
        self.stage = stage


def dispatch(source_format: str):
    """Return the conversion function for the given source format.

    Returns a callable(input_path, output_glb_path) -> None.
    """
    from app.features.conversion.pipelines import mesh_trimesh, ifc_convert

    if source_format == "ifc":
        return ifc_convert.run
    elif source_format in ("obj", "dae", "glb"):
        return mesh_trimesh.run
    else:
        raise ConversionError(f"Unsupported format: {source_format}", stage="dispatch")
