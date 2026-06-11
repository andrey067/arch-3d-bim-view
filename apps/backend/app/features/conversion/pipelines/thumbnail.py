"""Thumbnail pipeline — Blender headless render → WebP.

Receives a GLB file, positions a camera to frame the bounding box,
renders at configurable resolution, and saves as WebP.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from app.features.conversion.pipelines.common import ConversionError

logger = logging.getLogger(__name__)

# Blender Python script — imports a GLB, auto-frames camera, renders WebP.
_BLENDER_THUMBNAIL_SCRIPT = '''
import bpy
import sys
import mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
glb_path = argv[0]
output_path = argv[1]
width = int(argv[2])
height = int(argv[3])

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Remove default camera and light
for obj in bpy.data.objects:
    if obj.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(obj, do_unlink=True)

# Import GLB
bpy.ops.import_scene.gltf(filepath=glb_path)

# Verify we imported something
mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objects:
    print("ERROR: No mesh objects found after import", file=sys.stderr)
    sys.exit(1)

# Calculate bounding box of all mesh objects
bbox_min = mathutils.Vector((float('inf'), float('inf'), float('inf')))
bbox_max = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))

for obj in mesh_objects:
    for vertex in obj.bound_box:
        world_vertex = obj.matrix_world @ mathutils.Vector(vertex)
        bbox_min.x = min(bbox_min.x, world_vertex.x)
        bbox_min.y = min(bbox_min.y, world_vertex.y)
        bbox_min.z = min(bbox_min.z, world_vertex.z)
        bbox_max.x = max(bbox_max.x, world_vertex.x)
        bbox_max.y = max(bbox_max.y, world_vertex.y)
        bbox_max.z = max(bbox_max.z, world_vertex.z)

# Center and size of bounding box
center = (bbox_min + bbox_max) / 2.0
size = (bbox_max - bbox_min).length

if size < 0.001:
    size = 1.0  # Fallback for degenerate models

# Create camera
cam_data = bpy.data.cameras.new("ThumbnailCamera")
cam_data.lens = 50  # 50mm focal length
cam_obj = bpy.data.objects.new("ThumbnailCamera", cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# Position camera: 45 degrees elevation, 30 degrees azimuth
# Distance: enough to frame the entire model with some margin
distance = size * 1.8
elevation = math.radians(30)
azimuth = math.radians(45)

cam_obj.location = center + mathutils.Vector((
    distance * math.cos(elevation) * math.cos(azimuth),
    distance * math.cos(elevation) * math.sin(azimuth),
    distance * math.sin(elevation),
))

# Point camera at center of bounding box
direction = center - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

# Create sun light
light_data = bpy.data.lights.new("ThumbnailSun", type='SUN')
light_data.energy = 3.0
light_obj = bpy.data.objects.new("ThumbnailSun", light_data)
bpy.context.scene.collection.objects.link(light_obj)
light_obj.location = center + mathutils.Vector((size, -size, size * 2))
light_obj.rotation_euler = (math.radians(45), 0, math.radians(45))

# Create fill light (softer, from opposite side)
fill_data = bpy.data.lights.new("ThumbnailFill", type='SUN')
fill_data.energy = 1.0
fill_obj = bpy.data.objects.new("ThumbnailFill", fill_data)
bpy.context.scene.collection.objects.link(fill_obj)
fill_obj.location = center + mathutils.Vector((-size, size, size))
fill_obj.rotation_euler = (math.radians(-30), 0, math.radians(-135))

# Setup render settings
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = width
scene.render.resolution_y = height
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'WEBP'
scene.render.image_settings.quality = 80
scene.render.film_transparent = True  # Transparent background

# Set world background to light gray
world = bpy.data.worlds.get("World")
if world is None:
    world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = (0.9, 0.9, 0.9, 1.0)

# Render
scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)

print(f"Thumbnail rendered: {width}x{height} → {output_path}")
'''

import math


def render(
    glb_path: Path,
    output_webp_path: Path,
    size: tuple[int, int] = (800, 600),
) -> None:
    """Render a thumbnail WebP from a GLB file using Blender headless.

    Args:
        glb_path: Path to the input GLB file.
        output_webp_path: Destination path for the .webp output.
        size: Tuple of (width, height) in pixels. Default (800, 600).

    Raises:
        ConversionError: If import, rendering, or export fails.
    """
    if not glb_path.exists():
        raise ConversionError(
            f"GLB file not found: {glb_path}", stage="thumbnail_validation"
        )

    width, height = size
    if width <= 0 or height <= 0:
        raise ConversionError(
            f"Invalid thumbnail size: {size}", stage="thumbnail_validation"
        )

    script_path = Path(tempfile.mktemp(suffix=".py"))
    try:
        script_path.write_text(_BLENDER_THUMBNAIL_SCRIPT)

        result = subprocess.run(
            [
                "blender",
                "--background",
                "--python",
                str(script_path),
                "--",
                str(glb_path),
                str(output_webp_path),
                str(width),
                str(height),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise ConversionError(
                f"Blender thumbnail render failed (exit {result.returncode}): "
                f"{result.stderr[-500:]}",
                stage="thumbnail_blender_render",
            )
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(
            "Blender thumbnail render timed out after 120s.",
            stage="thumbnail_blender_timeout",
        ) from exc
    except ConversionError:
        raise
    except FileNotFoundError as exc:
        raise ConversionError(
            "Blender binary not found. Ensure 'blender' is in PATH.",
            stage="thumbnail_blender_not_found",
        ) from exc
    finally:
        script_path.unlink(missing_ok=True)

    if not output_webp_path.exists() or output_webp_path.stat().st_size == 0:
        raise ConversionError(
            "Thumbnail output is empty or missing after render.",
            stage="thumbnail_output",
        )

    # Validate WebP header (RIFF....WEBP)
    with open(output_webp_path, "rb") as f:
        header = f.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
            raise ConversionError(
                "Thumbnail output is not a valid WebP file.",
                stage="thumbnail_validation",
            )

    logger.info(
        "Thumbnail render complete: %s (%dx%d) → %s",
        glb_path.name,
        width,
        height,
        output_webp_path.name,
    )
