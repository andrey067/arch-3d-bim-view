"""DAE/OBJ → GLB → normalize → USDZ → WebP thumbnail pipeline."""

from __future__ import annotations

import logging
import os

from glb_normalize import GlbNormalizeError, normalize_glb_for_ar
from mesh_to_glb import DAE_NAME, OBJ_NAME, MeshConversionFailure, convert_mesh_to_glb
from render_thumbnail import render_glb_thumbnail_or_placeholder
from usd_converter import UsdConversionError, glb_to_usdz

logger = logging.getLogger("arch3dar.converter.mesh")

GLB_NAME = "model.glb"
USDZ_NAME = "model.usdz"
THUMB_NAME = "thumbnail.webp"


class ConversionFailure(RuntimeError):
    pass


def run_mesh_pipeline(
    mesh_bytes: bytes,
    out_dir: str,
    *,
    mesh_format: str,
    blender_path: str | None,
    mesh_timeout_s: int,
    ar_max_extent_m: float,
) -> None:
    fmt = mesh_format.lower().strip()
    if fmt not in ("dae", "obj"):
        raise ConversionFailure(f"unsupported mesh format: {mesh_format}")

    original_name = DAE_NAME if fmt == "dae" else OBJ_NAME
    mesh_path = os.path.join(out_dir, original_name)
    glb_path = os.path.join(out_dir, GLB_NAME)
    usdz_path = os.path.join(out_dir, USDZ_NAME)
    webp_path = os.path.join(out_dir, THUMB_NAME)

    with open(mesh_path, "wb") as f:
        f.write(mesh_bytes)

    try:
        convert_mesh_to_glb(
            mesh_path,
            glb_path,
            mesh_format=fmt,
            blender_path=blender_path,
            timeout_s=mesh_timeout_s,
        )
    except MeshConversionFailure as e:
        raise ConversionFailure(str(e)) from e

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise ConversionFailure(f"empty GLB output from {fmt.upper()}")

    try:
        normalize_glb_for_ar(glb_path, ar_max_extent_m)
    except GlbNormalizeError as e:
        raise ConversionFailure(f"GLB normalize failed: {e}") from e

    try:
        glb_to_usdz(glb_path, usdz_path)
    except UsdConversionError as e:
        raise ConversionFailure(f"USDZ conversion failed: {e}") from e

    render_glb_thumbnail_or_placeholder(
        glb_path,
        webp_path,
        blender_path=blender_path,
        timeout_s=min(mesh_timeout_s, 90),
    )
    logger.info(
        "%s pipeline done → GLB %d bytes, USDZ %d bytes, thumb %d bytes",
        fmt.upper(),
        os.path.getsize(glb_path),
        os.path.getsize(usdz_path),
        os.path.getsize(webp_path),
    )
