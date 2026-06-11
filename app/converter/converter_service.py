"""Arch3DAR model-conversion worker — IFC/DAE/OBJ → GLB → USDZ on local disk."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ifc_pipeline import ConversionFailure as IfcConversionFailure
from ifc_pipeline import run_ifc_pipeline
from mesh_pipeline import ConversionFailure as MeshConversionFailure
from mesh_pipeline import run_mesh_pipeline

logger = logging.getLogger("arch3dar.converter")
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)

DATA_ROOT = os.environ.get("DATA_ROOT", "/data")
IFCCONVERT_PATH = os.environ.get("IFCCONVERT_PATH", "/usr/local/bin/IfcConvert")
BLENDER_PATH = os.environ.get("BLENDER_PATH", "blender")
IFC_CONVERSION_TIMEOUT_S = int(
    os.environ.get("IFC_CONVERSION_TIMEOUT_S", os.environ.get("CONVERSION_TIMEOUT_S", "120"))
)
MESH_CONVERSION_TIMEOUT_S = int(
    os.environ.get(
        "MESH_CONVERSION_TIMEOUT_S",
        os.environ.get("SKP_CONVERSION_TIMEOUT_S", "180"),
    )
)
AR_MAX_EXTENT_M = float(os.environ.get("AR_MAX_EXTENT_M", "2"))

GLB_NAME = "model.glb"
USDZ_NAME = "model.usdz"
THUMB_NAME = "thumbnail.webp"


class ConvertResponse(BaseModel):
    glbPath: str
    usdzPath: str
    thumbnailPath: str
    durationMs: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(DATA_ROOT, exist_ok=True)
    yield


app = FastAPI(title="Arch3DAR Converter", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


def _project_dir(project_id: str) -> str:
    path = os.path.join(DATA_ROOT, "projects", project_id)
    os.makedirs(path, exist_ok=True)
    return path


@app.post("/convert")
async def convert(
    projectId: str = Form(...),
    sourceFormat: str = Form("ifc"),
    file: UploadFile = File(...),
) -> ConvertResponse:
    """Convert IFC, DAE, or OBJ upload to GLB, USDZ, and WebP thumbnail on local disk.

    Form fields: projectId (UUID), sourceFormat (ifc|dae|obj), file (binary).
    Returns glbPath, usdzPath, thumbnailPath (under projects/{id}/), durationMs.
    """
    started = time.monotonic()
    fmt = sourceFormat.lower().strip()
    if fmt not in ("ifc", "dae", "obj"):
        raise HTTPException(status_code=400, detail="sourceFormat must be ifc, dae, or obj")

    source_bytes = await file.read()
    if not source_bytes:
        raise HTTPException(status_code=400, detail="empty upload")

    try:
        await asyncio.to_thread(_run_pipeline, source_bytes, projectId, fmt)
    except (IfcConversionFailure, MeshConversionFailure) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    rel = f"projects/{projectId}"
    duration_ms = int((time.monotonic() - started) * 1000)
    return ConvertResponse(
        glbPath=f"{rel}/{GLB_NAME}",
        usdzPath=f"{rel}/{USDZ_NAME}",
        thumbnailPath=f"{rel}/{THUMB_NAME}",
        durationMs=duration_ms,
    )


def _run_pipeline(source_bytes: bytes, project_id: str, source_format: str) -> None:
    out_dir = _project_dir(project_id)
    if source_format in ("dae", "obj"):
        run_mesh_pipeline(
            source_bytes,
            out_dir,
            mesh_format=source_format,
            blender_path=BLENDER_PATH,
            mesh_timeout_s=MESH_CONVERSION_TIMEOUT_S,
            ar_max_extent_m=AR_MAX_EXTENT_M,
        )
    else:
        run_ifc_pipeline(
            source_bytes,
            out_dir,
            ifcconvert_path=IFCCONVERT_PATH,
            conversion_timeout_s=IFC_CONVERSION_TIMEOUT_S,
            ar_max_extent_m=AR_MAX_EXTENT_M,
            blender_path=BLENDER_PATH,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("converter_service:app", host="0.0.0.0", port=8080)
