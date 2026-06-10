"""Arch3DAR model-conversion worker.

A small FastAPI service that:
- exposes `POST /convert` accepting a multipart upload (field "file") plus a
  form field "projectId"; returns GLB and thumbnail keys;
- is called synchronously by the .NET backend right after the upload.

No background loop, no Postgres queue. The backend awaits the conversion
inline and the worker just transforms the bytes it was given.
"""

from __future__ import annotations

import io
import logging
import os
import subprocess
import tempfile
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

logger = logging.getLogger("arch3dar.converter")
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)

IFCCONVERT_PATH = os.environ.get("IFCCONVERT_PATH", "/usr/local/bin/IfcConvert")
CONVERSION_TIMEOUT_S = int(os.environ.get("CONVERSION_TIMEOUT_S", "120"))
MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "false").lower() == "true"
MINIO_BUCKET_GLB = os.environ.get("MINIO_BUCKET_GLB", "glb-files")
MINIO_BUCKET_THUMBNAILS = os.environ.get("MINIO_BUCKET_THUMBNAILS", "thumbnails")


def make_minio() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL,
    )


minio_client = make_minio()


class ConvertResponse(BaseModel):
    glbKey: str
    usdzKey: str
    thumbnailKey: str
    durationMs: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Arch3DAR Converter", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


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
        glb_bytes, usdz_bytes, thumb_bytes = await asyncio.to_thread(_run_ifc_convert, ifc_bytes, projectId)
    except ConversionFailure as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    glb_key = f"projects/{projectId}/model.glb"
    usdz_key = f"projects/{projectId}/model.usdz"
    thumb_key = f"projects/{projectId}/thumb.png"

    try:
        minio_client.put_object(
            MINIO_BUCKET_GLB, glb_key,
            io.BytesIO(glb_bytes), length=len(glb_bytes), content_type="model/gltf-binary",
        )
        minio_client.put_object(
            MINIO_BUCKET_GLB, usdz_key,
            io.BytesIO(usdz_bytes), length=len(usdz_bytes), content_type="model/vnd.usdz+zip",
        )
        minio_client.put_object(
            MINIO_BUCKET_THUMBNAILS, thumb_key,
            io.BytesIO(thumb_bytes), length=len(thumb_bytes), content_type="image/png",
        )
    except S3Error as e:
        logger.exception("minio upload failed: %s", e)
        raise HTTPException(status_code=502, detail=f"minio upload failed: {e}") from e

    duration_ms = int((time.monotonic() - started) * 1000)
    return ConvertResponse(glbKey=glb_key, usdzKey=usdz_key, thumbnailKey=thumb_key, durationMs=duration_ms)


class ConversionFailure(RuntimeError):
    pass


def _run_ifc_convert(ifc_bytes: bytes, project_id: str) -> tuple[bytes, bytes, bytes]:
    """Run IfcConvert synchronously, producing GLB, USDZ, and thumbnail bytes.

    Strips CRLF line endings before invoking IfcConvert because some
    Revit exports use CRLF and v0.7.11 has a parser regression on it.
    """
    import asyncio
    import re
    import zipfile
    from PIL import Image
    import numpy as np
    import trimesh
    from pxr import Usd, UsdGeom, Sdf, Gf, Vt

    # Normalize CRLF -> LF in-place on a copy; this fixes a known parser
    # regression in IfcConvert 0.7.11 with Windows-line-end files.
    ifc_bytes = ifc_bytes.replace(b"\r\n", b"\n")

    with tempfile.TemporaryDirectory() as td:
        ifc_path = os.path.join(td, "model.ifc")
        glb_path = os.path.join(td, "model.glb")
        png_path = os.path.join(td, "thumb.png")

        with open(ifc_path, "wb") as f:
            f.write(ifc_bytes)

        try:
            proc = subprocess.run(
                [IFCCONVERT_PATH, ifc_path, glb_path],
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

        try:
            thumb_proc = subprocess.run(
                [IFCCONVERT_PATH, ifc_path, png_path, "--thumbnail"],
                capture_output=True,
                text=True,
                timeout=CONVERSION_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired as e:
            raise ConversionFailure("thumbnail timeout") from e

        if thumb_proc.returncode != 0:
            img = Image.new("RGB", (320, 240), color=(220, 220, 220))
            img.save(png_path)

        with open(glb_path, "rb") as f:
            glb_bytes = f.read()
        with open(png_path, "rb") as f:
            thumb_bytes = f.read()

        if not glb_bytes:
            raise ConversionFailure("empty GLB output")

        # --- GLB → USDZ conversion via trimesh + OpenUSD ---
        try:
            scene = trimesh.load(glb_path)
            usda_path = os.path.join(td, "model.usda")
            stage = Usd.Stage.CreateNew(usda_path)
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

            for name, geom in scene.geometry.items():
                if not isinstance(geom, trimesh.Trimesh):
                    continue
                safe = re.sub(r'^[^a-zA-Z_]', '_', name)
                safe = re.sub(r'[^a-zA-Z0-9_]', '_', safe)
                mesh_path = Sdf.Path(f'/Root/Mesh_{safe}')
                usd_mesh = UsdGeom.Mesh.Define(stage, mesh_path)
                verts = geom.vertices.astype(np.float64)
                usd_mesh.GetPointsAttr().Set(
                    Vt.Vec3fArray(len(verts), [Gf.Vec3f(*v) for v in verts])
                )
                face_counts = Vt.IntArray(len(geom.faces), [3] * len(geom.faces))
                face_indices = Vt.IntArray(len(geom.faces) * 3, geom.faces.flatten().tolist())
                usd_mesh.GetFaceVertexCountsAttr().Set(face_counts)
                usd_mesh.GetFaceVertexIndicesAttr().Set(face_indices)

            stage.GetRootLayer().Save()

            usdz_path = os.path.join(td, "model.usdz")
            with zipfile.ZipFile(usdz_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(usda_path, "model.usda")

            with open(usdz_path, "rb") as f:
                usdz_bytes = f.read()
            logger.info("USDZ conversion done: %d bytes", len(usdz_bytes))
        except Exception as e:
            logger.warning("USDZ conversion failed (GLB-only fallback): %s", e)
            usdz_bytes = b""

        return glb_bytes, usdz_bytes, thumb_bytes


# Late import (used only by the /convert handler).
import asyncio  # noqa: E402

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("converter_service:app", host="0.0.0.0", port=8080)
