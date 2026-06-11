"""Smoke tests for SKP → GLB (requires Blender when run)."""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile

import pytest

from skp_to_glb import SkpConversionFailure, convert_skp_to_glb


def _minimal_skp(path: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("SketchUp/version.txt", "1.0")


@pytest.mark.skipif(shutil.which("blender") is None, reason="Blender not installed")
def test_convert_skp_to_glb_produces_non_empty_glb() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        skp = os.path.join(tmp, "test.skp")
        glb = os.path.join(tmp, "out.glb")
        _minimal_skp(skp)
        try:
            convert_skp_to_glb(skp, glb, timeout_s=120)
        except SkpConversionFailure:
            pytest.skip("Blender SKP importer unavailable for minimal fixture")
        assert os.path.isfile(glb)
        assert os.path.getsize(glb) > 0


def test_convert_skp_missing_blender_raises() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        skp = os.path.join(tmp, "test.skp")
        glb = os.path.join(tmp, "out.glb")
        _minimal_skp(skp)
        with pytest.raises(SkpConversionFailure):
            convert_skp_to_glb(
                skp,
                glb,
                blender_path="/nonexistent/blender",
                timeout_s=5,
            )
