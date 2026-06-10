"""Arch3DAR model-conversion worker — IFC → GLB → USDZ on local disk."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import tempfile
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image
from pydantic import BaseModel

from glb_normalize import GlbNormalizeError, normalize_glb_for_ar
from usd_converter import UsdConversionError, glb_to_usdz

logger = logging.getLogger("arch3dar.converter")
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)

DATA_ROOT = os.environ.get("DATA_ROOT", "/data")
IFCCONVERT_PATH = os.environ.get("IFCCONVERT_PATH", "/usr/local/bin/IfcConvert")
CONVERSION_TIMEOUT_S = int(os.environ.get("CONVERSION_TIMEOUT_S", "120"))
AR_MAX_EXTENT_M = float(os.environ.get("AR_MAX_EXTENT_M", "2"))

IFC_NAME = "original.ifc"
GLB_NAME = "model.glb"
USDZ_NAME = "model.usdz"
THUMB_NAME = "thumbnail.png"


class ConvertResponse(BaseModel):
    glbPath: str
    usdzPath: str
    thumbnailPath: str
    durationMs: int


class ConversionFailure(RuntimeError):
    pass


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
    file: UploadFile = File(...),
) -> ConvertResponse:
    started = time.monotonic()

    ifc_bytes = await file.read()
    if not ifc_bytes:
        raise HTTPException(status_code=400, detail="empty upload")

    try:
        await asyncio.to_thread(_run_pipeline, ifc_bytes, projectId)
    except ConversionFailure as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except UsdConversionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GlbNormalizeError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    rel = f"projects/{projectId}"
    duration_ms = int((time.monotonic() - started) * 1000)
    return ConvertResponse(
        glbPath=f"{rel}/{GLB_NAME}",
        usdzPath=f"{rel}/{USDZ_NAME}",
        thumbnailPath=f"{rel}/{THUMB_NAME}",
        durationMs=duration_ms,
    )


def _run_pipeline(ifc_bytes: bytes, project_id: str) -> None:
    ifc_bytes = ifc_bytes.replace(b"\r\n", b"\n")
    out_dir = _project_dir(project_id)
    ifc_path = os.path.join(out_dir, IFC_NAME)
    glb_path = os.path.join(out_dir, GLB_NAME)
    usdz_path = os.path.join(out_dir, USDZ_NAME)
    png_path = os.path.join(out_dir, THUMB_NAME)

    with open(ifc_path, "wb") as f:
        f.write(ifc_bytes)

    try:
        proc = subprocess.run(
            [IFCCONVERT_PATH, "-y", ifc_path, glb_path],
            capture_output=True,
            text=True,
            timeout=CONVERSION_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as e:
        raise ConversionFailure("conversion timeout") from e
    except FileNotFoundError as e:
        raise ConversionFailure("IfcConvert binary not found") from e

    if proc.returncode != 0:
        raise ConversionFailure(
            f"IfcConvert exited {proc.returncode}: {proc.stderr.strip()[:200]}"
        )

    if not os.path.isfile(glb_path) or os.path.getsize(glb_path) == 0:
        raise ConversionFailure("empty GLB output")

    try:
        thumb_proc = subprocess.run(
            [IFCCONVERT_PATH, "-y", ifc_path, png_path, "--thumbnail"],
            capture_output=True,
            text=True,
            timeout=CONVERSION_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired as e:
        raise ConversionFailure("thumbnail timeout") from e

    if thumb_proc.returncode != 0 or not os.path.isfile(png_path):
        Image.new("RGB", (320, 240), color=(220, 220, 220)).save(png_path)

    normalize_glb_for_ar(glb_path, AR_MAX_EXTENT_M)
    glb_to_usdz(glb_path, usdz_path)
    logger.info("Converted project %s → GLB %d bytes, USDZ %d bytes",
                project_id, os.path.getsize(glb_path), os.path.getsize(usdz_path))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("converter_service:app", host="0.0.0.0", port=8080)
