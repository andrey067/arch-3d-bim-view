"""Shared pipeline utilities — dispatch, error types, normalization.

Maps source_format to the correct pipeline callable.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from app.features.models.models import SourceFormat

logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Raised when a conversion pipeline fails."""

    def __init__(self, message: str, *, stage: str = "unknown") -> None:
        super().__init__(message)
        self.stage = stage


def dispatch(source_format: SourceFormat) -> Callable[[Path, Path], None]:
    """Return the pipeline function for a given source format.

    Args:
        source_format: The detected source format.

    Returns:
        A callable(input_path, output_glb_path) that produces a GLB.

    Raises:
        NotImplementedError: For formats outside the MVP scope.
    """
    from app.features.conversion.pipelines.ifc import run as ifc_run
    from app.features.conversion.pipelines.mesh import run as mesh_run

    mapping: dict[SourceFormat, Callable[[Path, Path], None]] = {
        SourceFormat.ifc: ifc_run,
        SourceFormat.dae: mesh_run,
        SourceFormat.obj: mesh_run,
        SourceFormat.glb: mesh_run,
    }

    fn = mapping.get(source_format)
    if fn is None:
        raise NotImplementedError(
            f"Format '{source_format.value}' has no conversion pipeline."
        )
    return fn
