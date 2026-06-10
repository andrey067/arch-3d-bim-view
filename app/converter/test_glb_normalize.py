"""Unit tests for glb_normalize."""

from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest

from glb_normalize import GlbNormalizeError, normalize_glb_for_ar


def _write_glb(path: str, gltf: dict, bin_data: bytes) -> None:
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


def _write_minimal_glb(path: str, positions: list[tuple[float, float, float]]) -> None:
    verts = b"".join(struct.pack("<3f", *p) for p in positions)
    indices = struct.pack("<3I", 0, 1, 2)
    bin_data = indices + verts
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    zs = [p[2] for p in positions]
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
                "min": [min(xs), min(ys), min(zs)],
                "max": [max(xs), max(ys), max(zs)],
            },
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]}],
        "nodes": [{"mesh": 0}],
        "scenes": [{"nodes": [0]}],
        "scene": 0,
    }
    _write_glb(path, gltf, bin_data)


class GlbNormalizeTests(unittest.TestCase):
    def test_scales_to_target_extent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            glb = os.path.join(td, "big.glb")
            _write_minimal_glb(glb, [(-10.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 2.0, 0.0)])
            normalize_glb_for_ar(glb, max_extent_m=0.5)
            with open(glb, "rb") as f:
                data = f.read()
            json_len = struct.unpack_from("<I", data, 12)[0]
            acc = json.loads(data[20 : 20 + json_len])["accessors"][1]
            extent = max(acc["max"][i] - acc["min"][i] for i in range(3))
            self.assertAlmostEqual(extent, 0.5, places=4)
            self.assertAlmostEqual(acc["min"][1], 0.0, places=4)

    def test_bakes_node_matrix_before_scaling(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            glb = os.path.join(td, "split.glb")
            # Two triangles far apart in world space via node matrices
            verts_a = struct.pack("<3f3f3f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
            verts_b = struct.pack("<3f3f3f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
            indices = struct.pack("<3I", 0, 1, 2)
            bin_data = indices + verts_a + indices + verts_b
            gltf = {
                "asset": {"version": "2.0"},
                "buffers": [{"byteLength": len(bin_data)}],
                "bufferViews": [
                    {"buffer": 0, "byteOffset": 0, "byteLength": 12},
                    {"buffer": 0, "byteOffset": 12, "byteLength": 36},
                    {"buffer": 0, "byteOffset": 48, "byteLength": 12},
                    {"buffer": 0, "byteOffset": 60, "byteLength": 36},
                ],
                "accessors": [
                    {"bufferView": 0, "componentType": 5125, "count": 3, "type": "SCALAR"},
                    {
                        "bufferView": 1,
                        "componentType": 5126,
                        "count": 3,
                        "type": "VEC3",
                        "min": [0, 0, 0],
                        "max": [1, 1, 0],
                    },
                    {"bufferView": 2, "componentType": 5125, "count": 3, "type": "SCALAR"},
                    {
                        "bufferView": 3,
                        "componentType": 5126,
                        "count": 3,
                        "type": "VEC3",
                        "min": [0, 0, 0],
                        "max": [1, 1, 0],
                    },
                ],
                "meshes": [
                    {"primitives": [{"attributes": {"POSITION": 1}, "indices": 0}]},
                    {"primitives": [{"attributes": {"POSITION": 3}, "indices": 2}]},
                ],
                "nodes": [
                    {"mesh": 0, "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]},
                    {"mesh": 1, "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 10, 0, 0, 1]},
                ],
                "scenes": [{"nodes": [0, 1]}],
                "scene": 0,
            }
            _write_glb(glb, gltf, bin_data)
            normalize_glb_for_ar(glb, max_extent_m=1.0)

            with open(glb, "rb") as f:
                data = f.read()
            json_len = struct.unpack_from("<I", data, 12)[0]
            baked = json.loads(data[20 : 20 + json_len])
            self.assertNotIn("matrix", baked["nodes"][0])
            acc_a = baked["accessors"][1]
            acc_b = baked["accessors"][3]
            gap = acc_b["min"][0] - acc_a["max"][0]
            self.assertGreater(gap, 0.1)

    def test_rejects_invalid_max_extent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            glb = os.path.join(td, "x.glb")
            _write_minimal_glb(glb, [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)])
            with self.assertRaises(GlbNormalizeError):
                normalize_glb_for_ar(glb, max_extent_m=0)


if __name__ == "__main__":
    unittest.main()
