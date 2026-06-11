"""IFC → GLB → normalize → USDZ → WebP thumbnail pipeline."""

from __future__ import annotations

import logging
import os
import subprocess

from glb_normalize import normalize_glb_for_ar
from render_thumbnail import render_glb_thumbnail_or_placeholder
from usd_converter import glb_to_usdz

logger = logging.getLogger("arch3dar.converter.ifc")

IFC_NAME = "original.ifc"
GLB_NAME = "model.glb"
USDZ_NAME = "model.usdz"
THUMB_NAME = "thumbnail.webp"


class ConversionFailure(RuntimeError):
    pass


def run_ifc_pipeline(
    ifc_bytes: bytes,
    out_dir: str,
    *,
    ifcconvert_path: str,
    conversion_timeout_s: int,
    ar_max_extent_m: float,
    blender_path: str | None = None,
) -> None:
    ifc_bytes = ifc_bytes.replace(b"\r\n", b"\n")
    ifc_path = os.path.join(out_dir, IFC_NAME)
    glb_path = os.path.join(out_dir, GLB_NAME)
    usdz_path = os.path.join(out_dir, USDZ_NAME)
    webp_path = os.path.join(out_dir, THUMB_NAME)

    with open(ifc_path, "wb") as f:
        f.write(ifc_bytes)

    try:
        proc = subprocess.run(
            [ifcconvert_path, "-y", ifc_path, glb_path],
            capture_output=True,
            text=True,
            timeout=conversion_timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise ConversionFailure("conversion timeout") from e
    except FileNotFoundError as e:
        raise ConversionFailure("IfcConvert binary not found") from e

    if proc.returncode != 0:
        raise ConversionFailure(
            f"IfcConvert exited {proc.returncode}: {proc.stderr.strip()[:200]}"
        )

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise ConversionFailure("empty GLB output")

    normalize_glb_for_ar(glb_path, ar_max_extent_m)
    glb_to_usdz(glb_path, usdz_path)
    render_glb_thumbnail_or_placeholder(
        glb_path,
        webp_path,
        blender_path=blender_path,
        timeout_s=min(conversion_timeout_s, 90),
    )
    logger.info(
        "IFC pipeline done → GLB %d bytes, USDZ %d bytes, thumb %d bytes",
        os.path.getsize(glb_path),
        os.path.getsize(usdz_path),
        os.path.getsize(webp_path),
    )
