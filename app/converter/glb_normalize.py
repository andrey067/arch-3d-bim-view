"""Bake node transforms, scale to tabletop size, and rest on Y=0 for AR preview."""

from __future__ import annotations

import json
import struct
from typing import Any


class GlbNormalizeError(RuntimeError):
    pass


def _read_glb(path: str) -> tuple[dict[str, Any], bytearray]:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 20:
        raise GlbNormalizeError("GLB too small")
    magic, version, _length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise GlbNormalizeError("unsupported GLB version")
    json_len = struct.unpack_from("<I", data, 12)[0]
    json_start = 20
    json_end = json_start + json_len
    gltf = json.loads(data[json_start:json_end])
    bin_len = struct.unpack_from("<I", data, json_end)[0]
    bin_start = json_end + 8
    bin_data = bytearray(data[bin_start : bin_start + bin_len])
    return gltf, bin_data


def _write_glb(path: str, gltf: dict[str, Any], bin_data: bytearray) -> None:
    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_bytes += b" " * json_pad
    bin_pad = (4 - len(bin_data) % 4) % 4
    bin_chunk = bytes(bin_data) + b"\x00" * bin_pad
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_chunk)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        f.write(json_bytes)
        f.write(struct.pack("<I4s", len(bin_chunk), b"BIN\x00"))
        f.write(bin_chunk)


def _transform_point(matrix: list[float], x: float, y: float, z: float) -> tuple[float, float, float]:
    return (
        matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
        matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
        matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
    )


def _mesh_position_accessor_ids(gltf: dict[str, Any], mesh_index: int) -> set[int]:
    ids: set[int] = set()
    mesh = gltf["meshes"][mesh_index]
    for prim in mesh.get("primitives", []):
        if "POSITION" in prim.get("attributes", {}):
            ids.add(prim["attributes"]["POSITION"])
    return ids


def _iter_positions(
    gltf: dict[str, Any], bin_data: bytearray, acc_id: int
) -> tuple[int, int, int]:
    accessors = gltf["accessors"]
    buffer_views = gltf["bufferViews"]
    acc = accessors[acc_id]
    bv = buffer_views[acc["bufferView"]]
    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = bv.get("byteStride", 12) or 12
    return byte_offset, stride, acc["count"]


def _read_position(bin_data: bytearray, off: int) -> tuple[float, float, float]:
    return struct.unpack_from("<3f", bin_data, off)


def _write_position(bin_data: bytearray, off: int, x: float, y: float, z: float) -> None:
    struct.pack_into("<3f", bin_data, off, x, y, z)


def _bake_node_transforms(gltf: dict[str, Any], bin_data: bytearray) -> None:
    """Apply node matrices to mesh vertices so IFC parts stay assembled."""
    nodes = gltf.get("nodes", [])
    for node in nodes:
        mesh_index = node.get("mesh")
        matrix = node.get("matrix")
        if mesh_index is None or matrix is None:
            continue

        for acc_id in _mesh_position_accessor_ids(gltf, mesh_index):
            byte_offset, stride, count = _iter_positions(gltf, bin_data, acc_id)
            for i in range(count):
                off = byte_offset + i * stride
                x, y, z = _read_position(bin_data, off)
                x, y, z = _transform_point(matrix, x, y, z)
                _write_position(bin_data, off, x, y, z)

            acc = gltf["accessors"][acc_id]
            acc.pop("min", None)
            acc.pop("max", None)

        node.pop("matrix", None)


def _position_accessor_ids(gltf: dict[str, Any]) -> set[int]:
    ids: set[int] = set()
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if "POSITION" in prim.get("attributes", {}):
                ids.add(prim["attributes"]["POSITION"])
    return ids


def _position_bounds(gltf: dict[str, Any], bin_data: bytearray) -> tuple[list[float], list[float]]:
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    for acc_id in _position_accessor_ids(gltf):
        byte_offset, stride, count = _iter_positions(gltf, bin_data, acc_id)
        for i in range(count):
            off = byte_offset + i * stride
            x, y, z = _read_position(bin_data, off)
            mins[0], mins[1], mins[2] = min(mins[0], x), min(mins[1], y), min(mins[2], z)
            maxs[0], maxs[1], maxs[2] = max(maxs[0], x), max(maxs[1], y), max(maxs[2], z)
    if mins[0] == float("inf"):
        raise GlbNormalizeError("no POSITION attributes in GLB")
    return mins, maxs


def _apply_to_positions(
    gltf: dict[str, Any],
    bin_data: bytearray,
    fn,
) -> None:
    for acc_id in _position_accessor_ids(gltf):
        byte_offset, stride, count = _iter_positions(gltf, bin_data, acc_id)
        mins = [float("inf")] * 3
        maxs = [float("-inf")] * 3
        for i in range(count):
            off = byte_offset + i * stride
            x, y, z = _read_position(bin_data, off)
            x, y, z = fn(x, y, z)
            _write_position(bin_data, off, x, y, z)
            mins[0], mins[1], mins[2] = min(mins[0], x), min(mins[1], y), min(mins[2], z)
            maxs[0], maxs[1], maxs[2] = max(maxs[0], x), max(maxs[1], y), max(maxs[2], z)
        acc = gltf["accessors"][acc_id]
        acc["min"] = mins
        acc["max"] = maxs


def normalize_glb_for_ar(glb_path: str, max_extent_m: float) -> None:
    """Bake IFC node transforms, scale to tabletop size, center on X/Z, rest on Y=0."""
    if max_extent_m <= 0:
        raise GlbNormalizeError("max_extent_m must be positive")

    gltf, bin_data = _read_glb(glb_path)
    _bake_node_transforms(gltf, bin_data)

    mins, maxs = _position_bounds(gltf, bin_data)
    center = [(mins[i] + maxs[i]) / 2.0 for i in range(3)]
    extent = max(maxs[i] - mins[i] for i in range(3))
    if extent <= 0:
        raise GlbNormalizeError("degenerate model bounds")

    scale = max_extent_m / extent

    def center_and_scale(x: float, y: float, z: float) -> tuple[float, float, float]:
        return (
            (x - center[0]) * scale,
            (y - center[1]) * scale,
            (z - center[2]) * scale,
        )

    _apply_to_positions(gltf, bin_data, center_and_scale)

    mins, maxs = _position_bounds(gltf, bin_data)
    y_lift = -mins[1]

    def lift_to_surface(x: float, y: float, z: float) -> tuple[float, float, float]:
        return (x, y + y_lift, z)

    _apply_to_positions(gltf, bin_data, lift_to_surface)
    _write_glb(glb_path, gltf, bin_data)
