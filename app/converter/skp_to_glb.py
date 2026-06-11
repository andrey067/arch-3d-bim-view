"""Blender headless: SKP → GLB. Callable as subprocess or inside Blender (--python)."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

logger = logging.getLogger("arch3dar.converter.skp")

SKP_NAME = "original.skp"
GLB_NAME = "model.glb"


class SkpConversionFailure(RuntimeError):
    pass


def convert_skp_to_glb(
    skp_path: str,
    glb_path: str,
    *,
    blender_path: str | None = None,
    timeout_s: int = 180,
) -> None:
    blender = blender_path or os.environ.get("BLENDER_PATH", "blender")
    script = os.path.abspath(__file__)
    cmd = [
        blender,
        "-b",
        "--python",
        script,
        "--",
        "--input",
        skp_path,
        "--output",
        glb_path,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        raise SkpConversionFailure("SKP conversion timeout") from e
    except FileNotFoundError as e:
        raise SkpConversionFailure("Blender binary not found") from e

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:400]
        raise SkpConversionFailure(f"Blender SKP import failed: {detail}")

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise SkpConversionFailure("empty GLB output from SKP")


def _parse_blender_args(argv: list[str]) -> argparse.Namespace:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def _import_skp_blender(input_path: str) -> None:
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)

    try:
        import addon_utils

        addon_utils.enable("io_sketchup", default_set=True, persistent=False)
    except Exception:
        pass

    last_error: Exception | None = None
    for op_name in ("skp", "sketchup"):
        op = getattr(bpy.ops.import_scene, op_name, None)
        if op is None:
            continue
        try:
            op(filepath=input_path)
            return
        except Exception as e:
            last_error = e

    raise SkpConversionFailure(
        f"SKP import operator unavailable or failed: {last_error}"
    )


def _blender_main() -> None:
    args = _parse_blender_args(sys.argv)
    import bpy

    _import_skp_blender(args.input)
    bpy.ops.export_scene.gltf(filepath=args.output, export_format="GLB")


try:
    import bpy  # type: ignore

    if __name__ == "__main__":
        _blender_main()
except ImportError:
    pass
