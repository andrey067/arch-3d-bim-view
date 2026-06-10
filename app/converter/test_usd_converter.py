"""Smoke tests for usd_converter (skipped when usd_from_gltf is not installed)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from usd_converter import USD_FROM_GLTF_PATH, glb_to_usdz


def _has_usd_tool() -> bool:
    return os.path.isfile(USD_FROM_GLTF_PATH) and os.access(USD_FROM_GLTF_PATH, os.X_OK)


@unittest.skipUnless(_has_usd_tool(), "usd_from_gltf not available")
class UsdConverterTests(unittest.TestCase):
  def test_glb_to_usdz_produces_non_empty_zip(self) -> None:
    # Minimal valid GLB header (length 12) — usd_from_gltf may reject; use IfcConvert output in CI.
    # This test uses a tiny GLB from glTF sample if present, else skip content validation.
    with tempfile.TemporaryDirectory() as td:
      glb = os.path.join(td, "cube.glb")
      usdz = os.path.join(td, "cube.usdz")
      # 12-byte GLB header placeholder — real CI should use a fixture GLB from integration tests.
      if not os.environ.get("ARCH3DAR_TEST_GLB"):
        self.skipTest("Set ARCH3DAR_TEST_GLB to a real GLB path for conversion test")
      shutil.copy(os.environ["ARCH3DAR_TEST_GLB"], glb)
      glb_to_usdz(glb, usdz)
      self.assertGreater(os.path.getsize(usdz), 0)
      with zipfile.ZipFile(usdz) as zf:
        self.assertGreater(len(zf.namelist()), 0)


if __name__ == "__main__":
  unittest.main()
