"""USDZ conversion — GLB → USDZ via usd_from_gltf CLI.

usd_from_gltf is a tool from the USD toolkit that converts
glTF/GLB files to USDZ format for iOS Quick Look AR.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from app.features.conversion.pipelines.common import ConversionError

logger = logging.getLogger(__name__)


def run(glb_path: Path, output_usdz_path: Path) -> None:
    """Convert GLB to USDZ using usd_from_gltf."""
    if not glb_path.exists():
        raise ConversionError(f"GLB not found: {glb_path}", stage="usdz_validation")

    from app.core.config import get_settings
    settings = get_settings()
    usd_from_gltf = shutil.which(settings.USD_FROM_GLTF_PATH) or settings.USD_FROM_GLTF_PATH
    if not shutil.which(usd_from_gltf) and not Path(usd_from_gltf).is_file():
        raise ConversionError(
            "usd_from_gltf not found. Set USD_FROM_GLTF_PATH or install the USD toolkit.",
            stage="usdz_check",
        )

    try:
        result = subprocess.run(
            [usd_from_gltf, str(glb_path), str(output_usdz_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise ConversionError(
                f"usd_from_gltf failed (exit {result.returncode}): {result.stderr[-500:]}",
                stage="usdz_convert",
            )

    except subprocess.TimeoutExpired as exc:
        raise ConversionError(
            "usd_from_gltf timed out after 120s.",
            stage="usdz_timeout",
        ) from exc
    except FileNotFoundError as exc:
        raise ConversionError(
            "usd_from_gltf binary not found.",
            stage="usdz_not_found",
        ) from exc

    if not output_usdz_path.exists() or output_usdz_path.stat().st_size == 0:
        raise ConversionError(
            "USDZ output is empty or missing.",
            stage="usdz_export",
        )

    logger.info("USDZ conversion complete: %s → %s", glb_path.name, output_usdz_path.name)
