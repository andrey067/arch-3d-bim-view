"""Blender headless: DAE/OBJ → GLB. Callable as subprocess or inside Blender (--python)."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

logger = logging.getLogger("arch3dar.converter.mesh")

DAE_NAME = "original.dae"
OBJ_NAME = "original.obj"
GLB_NAME = "model.glb"


class MeshConversionFailure(RuntimeError):
    pass


def convert_mesh_to_glb(
    input_path: str,
    glb_path: str,
    *,
    mesh_format: str,
    blender_path: str | None = None,
    timeout_s: int = 180,
) -> None:
    fmt = mesh_format.lower().strip()
    if fmt not in ("dae", "obj"):
        raise MeshConversionFailure(f"unsupported mesh format: {mesh_format}")

    blender = blender_path or os.environ.get("BLENDER_PATH", "blender")
    script = os.path.abspath(__file__)
    cmd = [
        blender,
        "-b",
        "--python",
        script,
        "--",
        "--input",
        input_path,
        "--output",
        glb_path,
        "--format",
        fmt,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        raise MeshConversionFailure("mesh conversion timeout") from e
    except FileNotFoundError as e:
        raise MeshConversionFailure("Blender binary not found") from e

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:400]
        raise MeshConversionFailure(f"Blender {fmt.upper()} import failed: {detail}")

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise MeshConversionFailure(f"empty GLB output from {fmt.upper()}")


def _parse_blender_args(argv: list[str]) -> argparse.Namespace:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", required=True, choices=("dae", "obj"))
    return parser.parse_args(argv)


def _enable_addon(mod_name: str) -> None:
    try:
        import addon_utils

        addon_utils.enable(mod_name, default_set=True, persistent=False)
    except Exception as e:  # pragma: no cover - addon enable is best-effort
        logger.warning("could not enable addon %s: %s", mod_name, e)


def _import_mesh_blender(input_path: str, mesh_format: str) -> None:
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)

    if mesh_format == "dae":
        # Blender 4.2 keeps Collada as a legacy addon: operator is wm.collada_import,
        # not import_scene.dae. import_units=True respects the <unit meter="..."> the
        # file declares (SketchUp exports use inches, meter="0.0254").
        _enable_addon("io_scene_collada")
        try:
            bpy.ops.wm.collada_import(filepath=input_path, import_units=True)
        except (AttributeError, RuntimeError) as e:
            raise MeshConversionFailure(f"DAE import operator unavailable: {e}") from e
    elif mesh_format == "obj":
        # Blender 4.x ships the new obj importer under wm.obj_import; the legacy one
        # under import_scene.obj was removed.
        if hasattr(bpy.ops.wm, "obj_import"):
            bpy.ops.wm.obj_import(filepath=input_path)
        elif hasattr(bpy.ops.import_scene, "obj"):
            bpy.ops.import_scene.obj(filepath=input_path)
        else:
            raise MeshConversionFailure("OBJ import operator unavailable")
    else:
        raise MeshConversionFailure(f"unsupported mesh format: {mesh_format}")

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise MeshConversionFailure(
            f"no mesh objects in scene after {mesh_format.upper()} import"
        )


def _blender_main() -> None:
    args = _parse_blender_args(sys.argv)
    import bpy

    _import_mesh_blender(args.input, args.format)
    _enable_addon("io_scene_gltf2")
    bpy.ops.export_scene.gltf(filepath=args.output, export_format="GLB")


try:
    import bpy  # type: ignore

    if __name__ == "__main__":
        _blender_main()
except ImportError:
    pass
