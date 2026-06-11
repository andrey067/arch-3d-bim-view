"""Mesh conversion pipeline — Blender headless for DAE/OBJ/GLB → GLB.

Handles Collada (DAE), Wavefront OBJ, and GLB normalization through
Blender's native importers. GLB files are re-exported with axis/scale
normalization (no reconversion, just canonicalization).
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from app.features.conversion.pipelines.common import ConversionError
from app.features.models.models import SourceFormat

logger = logging.getLogger(__name__)

# Blender Python script — imports the source file and exports canonical GLB.
_BLENDER_CONVERT_SCRIPT = '''
import bpy
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
source_format = argv[0]
input_path = argv[1]
output_path = argv[2]

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import based on format
if source_format == "dae":
    bpy.ops.wm.collada_import(filepath=input_path)
elif source_format == "obj":
    bpy.ops.wm.obj_import(filepath=input_path)
elif source_format == "glb":
    bpy.ops.import_scene.gltf(filepath=input_path)
else:
    print(f"ERROR: unsupported format {source_format}", file=sys.stderr)
    sys.exit(1)

# Verify we imported something
mesh_objects = [o for o in bpy.data.objects if o.type == 'MESH']
if not mesh_objects:
    print("ERROR: No mesh objects found after import", file=sys.stderr)
    sys.exit(1)

# Select all mesh objects for export
bpy.ops.object.select_all(action='DESELECT')
for obj in mesh_objects:
    obj.select_set(True)

# Export as GLB — canonical format with materials and textures
bpy.ops.export_scene.gltf(
    filepath=output_path,
    use_selection=True,
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
)
print(f"Exported GLB ({len(mesh_objects)} meshes) to {output_path}")
'''


def run(input_path: Path, output_glb_path: Path) -> None:
    """Convert a mesh file (DAE/OBJ/GLB) to canonical GLB via Blender.

    Args:
        input_path: Path to the source file (.dae, .obj, or .glb).
        output_glb_path: Destination path for the .glb output.

    Raises:
        ConversionError: If import or export fails.
    """
    if not input_path.exists():
        raise ConversionError(
            f"Input file not found: {input_path}", stage="mesh_validation"
        )

    # Detect format from extension
    ext = input_path.suffix.lstrip(".").lower()
    format_map = {
        "dae": SourceFormat.dae,
        "obj": SourceFormat.obj,
        "glb": SourceFormat.glb,
    }
    source_format = format_map.get(ext)
    if source_format is None:
        raise ConversionError(
            f"Unsupported mesh format: .{ext}", stage="mesh_format"
        )

    # For GLB, Blender just normalizes — but we can short-circuit if
    # the file is already valid and we trust the canonical form.
    # The MVP always goes through Blender for consistency.

    script_path = Path(tempfile.mktemp(suffix=".py"))
    try:
        script_path.write_text(_BLENDER_CONVERT_SCRIPT)

        result = subprocess.run(
            [
                "blender",
                "--background",
                "--python",
                str(script_path),
                "--",
                source_format.value,
                str(input_path),
                str(output_glb_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise ConversionError(
                f"Blender conversion failed (exit {result.returncode}): "
                f"{result.stderr[-500:]}",
                stage="mesh_blender_export",
            )
    except subprocess.TimeoutExpired as exc:
        raise ConversionError(
            "Blender conversion timed out after 300s.",
            stage="mesh_blender_timeout",
        ) from exc
    except ConversionError:
        raise
    except FileNotFoundError as exc:
        raise ConversionError(
            "Blender binary not found. Ensure 'blender' is in PATH.",
            stage="mesh_blender_not_found",
        ) from exc
    finally:
        script_path.unlink(missing_ok=True)

    if not output_glb_path.exists() or output_glb_path.stat().st_size == 0:
        raise ConversionError(
            "GLB output is empty or missing after conversion.",
            stage="mesh_export",
        )

    logger.info(
        "Mesh conversion complete: %s (%s) → %s",
        input_path.name,
        source_format.value,
        output_glb_path.name,
    )
