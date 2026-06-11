"""Smoke tests for render_thumbnail — skipped when Blender is unavailable."""

from __future__ import annotations

import json
import os
import shutil
import struct
import tempfile
import unittest

from render_thumbnail import render_glb_thumbnail, write_placeholder_webp


def _write_minimal_glb(path: str) -> None:
    positions = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)]
    verts = b"".join(struct.pack("<3f", *p) for p in positions)
    indices = struct.pack("<3I", 0, 1, 2)
    bin_data = indices + verts
    gltf = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(bin_data)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 12, "target": 34963},
            {"buffer": 0, "byteOffset": 12, "byteLength": len(verts), "target": 34962},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5125, "count": 3, "type": "SCALAR"},
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": 3,
                "type": "VEC3",
                "min": [0.0, 0.0, 0.0],
                "max": [1.0, 1.0, 0.0],
            },
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * json_pad
    bin_pad = (4 - len(bin_data) % 4) % 4
    bin_chunk = bin_data + b"\x00" * bin_pad
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        f.write(json_bytes)
        f.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00"))
        f.write(bin_chunk)


def _blender_available() -> bool:
    blender = os.environ.get("BLENDER_PATH", "blender")
    return shutil.which(blender) is not None


class RenderThumbnailTests(unittest.TestCase):
    def test_placeholder_webp_is_non_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            webp = os.path.join(td, "thumb.webp")
            write_placeholder_webp(webp)
            self.assertTrue(os.path.isfile(webp))
            self.assertGreater(os.path.getsize(webp), 0)

    @unittest.skipUnless(_blender_available(), "Blender not installed")
    def test_glb_fixture_renders_non_empty_webp(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            glb = os.path.join(td, "model.glb")
            webp = os.path.join(td, "thumb.webp")
            _write_minimal_glb(glb)
            render_glb_thumbnail(glb, webp, timeout_s=120)
            self.assertTrue(os.path.isfile(webp))
            self.assertGreater(os.path.getsize(webp), 100)


if __name__ == "__main__":
    unittest.main()
