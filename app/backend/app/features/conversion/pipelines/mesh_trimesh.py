"""Mesh conversion pipeline — trimesh for OBJ/DAE/GLB → GLB.

Uses trimesh for fast, dependency-light mesh conversion.
Preserves materials and textures when available (solid color fallback).
For DAE: trimesh+pycollada is primary; assimp CLI is fallback.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from app.features.conversion.pipelines.common import ConversionError

logger = logging.getLogger(__name__)


def run(input_path: Path, output_glb_path: Path) -> None:
    """Convert OBJ/DAE/GLB to canonical GLB.

    Strategy:
    1. GLB passthrough (copy + validate)
    2. Try trimesh (fast, handles OBJ with MTL, DAE via pycollada, GLB)
    3. For DAE: fallback to assimp CLI if trimesh fails
    """
    if not input_path.exists():
        raise ConversionError(
            f"Input file not found: {input_path}", stage="mesh_validation"
        )

    ext = input_path.suffix.lstrip(".").lower()

    if ext == "glb":
        _passthrough_glb(input_path, output_glb_path)
        return

    # Try trimesh first
    try:
        _convert_with_trimesh(input_path, output_glb_path, ext)
        logger.info("trimesh conversion OK: %s → %s", input_path.name, output_glb_path.name)
        return
    except Exception as exc:
        logger.warning("trimesh failed for %s: %s", input_path.name, exc)
        if ext != "dae":
            raise ConversionError(
                f"trimesh conversion failed: {exc}", stage="mesh_trimesh"
            ) from exc

    # Fallback for DAE: try assimp CLI
    if ext == "dae":
        try:
            _convert_with_assimp_cli(input_path, output_glb_path)
            logger.info("assimp CLI conversion OK: %s → %s", input_path.name, output_glb_path.name)
            return
        except Exception as exc:
            raise ConversionError(
                f"Both trimesh and assimp failed for DAE. assimp: {exc}",
                stage="mesh_assimp",
            ) from exc

    raise ConversionError(f"No converter available for .{ext}", stage="mesh_dispatch")


def _convert_with_trimesh(input_path: Path, output_glb_path: Path, ext: str) -> None:
    """Convert using trimesh (with pycollada for DAE)."""
    import trimesh

    scene_or_mesh = trimesh.load(
        str(input_path),
        force="scene" if ext == "dae" else None,
        process=True,
    )

    if isinstance(scene_or_mesh, trimesh.Scene):
        glb_bytes = trimesh.exchange.gltf.export_glb(scene_or_mesh)
        output_glb_path.write_bytes(glb_bytes)
    elif isinstance(scene_or_mesh, trimesh.Trimesh):
        scene = trimesh.Scene(geometry=scene_or_mesh)
        glb_bytes = trimesh.exchange.gltf.export_glb(scene)
        output_glb_path.write_bytes(glb_bytes)
    else:
        raise ConversionError(
            f"trimesh returned unexpected type: {type(scene_or_mesh)}",
            stage="mesh_trimesh",
        )

    if not output_glb_path.exists() or output_glb_path.stat().st_size == 0:
        raise ConversionError("GLB output is empty after trimesh export.", stage="mesh_trimesh")


def _convert_with_assimp_cli(input_path: Path, output_glb_path: Path) -> None:
    """Fallback: convert DAE using assimp CLI → OBJ → trimesh → GLB.

    Uses the `assimp` command-line tool (assimp-utils package).
    Preserves materials/colors from the DAE file.
    """
    assimp_bin = shutil.which("assimp")
    if not assimp_bin:
        raise ConversionError(
            "assimp CLI not found in PATH. Install assimp-utils.",
            stage="mesh_assimp_check",
        )

    import tempfile
    import trimesh

    with tempfile.TemporaryDirectory(prefix="assimp_conv_") as tmp:
        intermediate_obj = Path(tmp) / "intermediate.obj"

        try:
            result = subprocess.run(
                [assimp_bin, "export", str(input_path), str(intermediate_obj), "obj"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise ConversionError(
                    f"assimp export failed (exit {result.returncode}): {result.stderr[-500:]}",
                    stage="mesh_assimp_export",
                )
        except subprocess.TimeoutExpired as exc:
            raise ConversionError(
                "assimp timed out after 120s.",
                stage="mesh_assimp_timeout",
            ) from exc

        if not intermediate_obj.exists() or intermediate_obj.stat().st_size == 0:
            raise ConversionError(
                "Intermediate OBJ is empty — DAE may contain no extractable geometry.",
                stage="mesh_assimp_extract",
            )

        # Load OBJ with trimesh and export as GLB
        scene_or_mesh = trimesh.load(str(intermediate_obj), process=True)
        if isinstance(scene_or_mesh, trimesh.Scene):
            glb_bytes = trimesh.exchange.gltf.export_glb(scene_or_mesh)
        elif isinstance(scene_or_mesh, trimesh.Trimesh):
            scene = trimesh.Scene(geometry=scene_or_mesh)
            glb_bytes = trimesh.exchange.gltf.export_glb(scene)
        else:
            raise ConversionError(
                f"Unexpected trimesh type from assimp OBJ: {type(scene_or_mesh)}",
                stage="mesh_assimp_to_glb",
            )

        output_glb_path.write_bytes(glb_bytes)

    if not output_glb_path.exists() or output_glb_path.stat().st_size == 0:
        raise ConversionError("GLB output is empty after assimp export.", stage="mesh_assimp")


def _passthrough_glb(input_path: Path, output_glb_path: Path) -> None:
    """GLB files are already canonical — just copy and validate."""
    data = input_path.read_bytes()
    if len(data) < 12:
        raise ConversionError("GLB file is too small to be valid.", stage="mesh_glb_validate")

    if data[:4] != b"glTF":
        raise ConversionError("File does not have GLB magic bytes.", stage="mesh_glb_validate")

    shutil.copy2(str(input_path), str(output_glb_path))
    logger.info("GLB passthrough: %s", input_path.name)
