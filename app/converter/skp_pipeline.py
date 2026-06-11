"""SKP → GLB → normalize → USDZ → WebP thumbnail pipeline."""

from __future__ import annotations

import logging
import os

from glb_normalize import normalize_glb_for_ar
from render_thumbnail import render_glb_thumbnail_or_placeholder
from skp_to_glb import SKP_NAME, SkpConversionFailure, convert_skp_to_glb
from usd_converter import glb_to_usdz

logger = logging.getLogger("arch3dar.converter.skp")

GLB_NAME = "model.glb"
USDZ_NAME = "model.usdz"
THUMB_NAME = "thumbnail.webp"


class ConversionFailure(RuntimeError):
    pass


def run_skp_pipeline(
    skp_bytes: bytes,
    out_dir: str,
    *,
    blender_path: str | None,
    skp_timeout_s: int,
    ar_max_extent_m: float,
) -> None:
    skp_path = os.path.join(out_dir, SKP_NAME)
    glb_path = os.path.join(out_dir, GLB_NAME)
    usdz_path = os.path.join(out_dir, USDZ_NAME)
    webp_path = os.path.join(out_dir, THUMB_NAME)

    with open(skp_path, "wb") as f:
        f.write(skp_bytes)

    try:
        convert_skp_to_glb(
            skp_path,
            glb_path,
            blender_path=blender_path,
            timeout_s=skp_timeout_s,
        )
    except SkpConversionFailure as e:
        raise ConversionFailure(str(e)) from e

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise ConversionFailure("empty GLB output from SKP")

    normalize_glb_for_ar(glb_path, ar_max_extent_m)
    glb_to_usdz(glb_path, usdz_path)
    render_glb_thumbnail_or_placeholder(
        glb_path,
        webp_path,
        blender_path=blender_path,
        timeout_s=min(skp_timeout_s, 90),
    )
    logger.info(
        "SKP pipeline done → GLB %d bytes, USDZ %d bytes, thumb %d bytes",
        os.path.getsize(glb_path),
        os.path.getsize(usdz_path),
        os.path.getsize(webp_path),
    )
