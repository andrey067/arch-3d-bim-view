"""IFC conversion pipeline — IfcConvert CLI → OBJ → trimesh → GLB.

Uses IfcConvert (from IfcOpenShell) to convert IFC to OBJ with materials,
then trimesh to convert OBJ → GLB.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.features.conversion.pipelines.common import ConversionError

logger = logging.getLogger(__name__)


def run(input_path: Path, output_glb_path: Path) -> None:
    """Convert IFC to GLB via IfcConvert + trimesh.

    Pipeline:
        1. IfcConvert IFC → intermediate OBJ (with materials)
        2. trimesh OBJ → GLB
    """
    if not input_path.exists():
        raise ConversionError(
            f"Input file not found: {input_path}", stage="ifc_validation"
        )

    from app.core.config import get_settings
    settings = get_settings()
    ifcconvert = shutil.which(settings.IFCCONVERT_PATH) or settings.IFCCONVERT_PATH
    if not shutil.which(ifcconvert) and not Path(ifcconvert).is_file():
        raise ConversionError(
            "IfcConvert not found. Set IFCCONVERT_PATH or install IfcOpenShell tools.",
            stage="ifc_check",
        )

    with tempfile.TemporaryDirectory(prefix="ifc_conv_") as tmp:
        intermediate_obj = Path(tmp) / "intermediate.obj"

        _run_ifcconvert(ifcconvert, input_path, intermediate_obj)
        _obj_to_glb(intermediate_obj, output_glb_path)

    if not output_glb_path.exists() or output_glb_path.stat().st_size == 0:
        raise ConversionError(
            "GLB output is empty or missing after conversion.",
            stage="ifc_export",
        )

    logger.info("IFC conversion complete: %s → %s", input_path.name, output_glb_path.name)


def _run_ifcconvert(ifcconvert_bin: str, ifc_path: Path, output_obj: Path) -> None:
    """Run IfcConvert CLI to convert IFC to OBJ."""
    try:
        result = subprocess.run(
            [
                ifcconvert_bin,
                str(ifc_path),
                str(output_obj),
                "--use-element-guids",
                "--generate-uvs",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise ConversionError(
                f"IfcConvert failed (exit {result.returncode}): {result.stderr[-500:]}",
                stage="ifc_convert",
            )

    except subprocess.TimeoutExpired as exc:
        raise ConversionError(
            "IfcConvert timed out after 300s.",
            stage="ifc_timeout",
        ) from exc
    except FileNotFoundError as exc:
        raise ConversionError(
            "IfcConvert binary not found.",
            stage="ifc_not_found",
        ) from exc

    if not output_obj.exists() or output_obj.stat().st_size == 0:
        raise ConversionError(
            "Intermediate OBJ is empty — IFC may contain no extractable geometry.",
            stage="ifc_extract",
        )


def _obj_to_glb(obj_path: Path, output_glb: Path) -> None:
    """Convert intermediate OBJ to GLB using trimesh."""
    import trimesh

    scene_or_mesh = trimesh.load(str(obj_path), process=True)

    if isinstance(scene_or_mesh, trimesh.Scene):
        glb_bytes = trimesh.exchange.gltf.export_glb(scene_or_mesh)
    elif isinstance(scene_or_mesh, trimesh.Trimesh):
        scene = trimesh.Scene(geometry=scene_or_mesh)
        glb_bytes = trimesh.exchange.gltf.export_glb(scene)
    else:
        raise ConversionError(
            f"Unexpected trimesh type: {type(scene_or_mesh)}", stage="ifc_to_glb"
        )

    output_glb.write_bytes(glb_bytes)

    if not output_glb.exists() or output_glb.stat().st_size == 0:
        raise ConversionError("GLB output is empty after trimesh export.", stage="ifc_to_glb")
