"""Blender headless: GLB → WebP thumbnail. Callable as subprocess or inside Blender (--python)."""

from __future__ import annotations

import argparse
import logging
import math
import os
import subprocess
import sys

from PIL import Image

logger = logging.getLogger("arch3dar.converter.thumbnail")

DEFAULT_SIZE_PX = 512


class ThumbnailRenderFailure(RuntimeError):
    pass


def render_glb_thumbnail(
    glb_path: str,
    webp_path: str,
    *,
    blender_path: str | None = None,
    size_px: int = DEFAULT_SIZE_PX,
    timeout_s: int = 60,
) -> None:
    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise ThumbnailRenderFailure("missing or empty GLB for thumbnail")

    blender = blender_path or os.environ.get("BLENDER_PATH", "blender")
    script = os.path.abspath(__file__)
    cmd = [
        blender,
        "-b",
        "--python",
        script,
        "--",
        "--input",
        glb_path,
        "--output",
        webp_path,
        "--size",
        str(size_px),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        raise ThumbnailRenderFailure("thumbnail render timeout") from e
    except FileNotFoundError as e:
        raise ThumbnailRenderFailure("Blender binary not found") from e

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:400]
        raise ThumbnailRenderFailure(f"Blender thumbnail render failed: {detail}")

    if not os.path.isfile(webp_path) or os.path.getsize(webp_path) == 0:
        raise ThumbnailRenderFailure("empty WebP thumbnail output")


def write_placeholder_webp(webp_path: str, size_px: int = DEFAULT_SIZE_PX) -> None:
    Image.new("RGB", (size_px, size_px), color=(235, 235, 235)).save(webp_path, "WEBP", quality=85)


def render_glb_thumbnail_or_placeholder(
    glb_path: str,
    webp_path: str,
    *,
    blender_path: str | None = None,
    size_px: int = DEFAULT_SIZE_PX,
    timeout_s: int = 60,
) -> None:
    try:
        render_glb_thumbnail(
            glb_path,
            webp_path,
            blender_path=blender_path,
            size_px=size_px,
            timeout_s=timeout_s,
        )
    except ThumbnailRenderFailure as e:
        logger.warning("Blender thumbnail failed (%s); writing placeholder WebP", e)
        write_placeholder_webp(webp_path, size_px)


def _parse_blender_args(argv: list[str]) -> argparse.Namespace:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE_PX)
    return parser.parse_args(argv)


def _render_in_blender(input_path: str, output_path: str, size_px: int) -> None:
    import bpy
    from mathutils import Vector

    bpy.ops.wm.read_factory_settings(use_empty=True)

    try:
        import addon_utils

        addon_utils.enable("io_scene_gltf2", default_set=True, persistent=False)
    except Exception:
        pass

    bpy.ops.import_scene.gltf(filepath=input_path)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise ThumbnailRenderFailure("no mesh in GLB")

    min_corner = Vector((math.inf, math.inf, math.inf))
    max_corner = Vector((-math.inf, -math.inf, -math.inf))
    for obj in meshes:
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            min_corner = Vector(
                (min(min_corner.x, world.x), min(min_corner.y, world.y), min(min_corner.z, world.z))
            )
            max_corner = Vector(
                (max(max_corner.x, world.x), max(max_corner.y, world.y), max(max_corner.z, world.z))
            )

    center = (min_corner + max_corner) / 2
    extent = max((max_corner - min_corner).length, 0.01)
    distance = extent * 2.2

    cam_data = bpy.data.cameras.new("ThumbCam")
    cam_obj = bpy.data.objects.new("ThumbCam", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    direction = Vector((1.0, -1.0, 0.85)).normalized()
    cam_obj.location = center + direction * distance
    cam_obj.rotation_euler = (cam_obj.location - center).to_track_quat("-Z", "Y").to_euler()

    light_data = bpy.data.lights.new("ThumbLight", type="AREA")
    light_data.energy = 800
    light_obj = bpy.data.objects.new("ThumbLight", light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = center + Vector((-1.5, 1.0, 2.5)) * extent
    light_obj.rotation_euler = (center - light_obj.location).to_track_quat("-Z", "Y").to_euler()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = size_px
    scene.render.resolution_y = size_px
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 85
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.92, 0.92, 0.92, 1.0)
    bg.inputs[1].default_value = 1.0

    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)


def _blender_main() -> None:
    args = _parse_blender_args(sys.argv)
    _render_in_blender(args.input, args.output, args.size)


try:
    import bpy  # type: ignore

    if __name__ == "__main__":
        _blender_main()
except ImportError:
    pass
