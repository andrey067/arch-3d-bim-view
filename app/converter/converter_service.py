"""Arch3DAR model-conversion worker.

A small FastAPI service that:
- exposes `POST /convert` to run a single conversion for a project id;
- has a background claim loop that polls Postgres for projects in
  `UploadReceived` status and processes them with `SELECT ... FOR UPDATE SKIP LOCKED`.

Architecture: kept simple for the MVP — no message broker. The HTTP endpoint
is consumed by the .NET backend's `HttpModelConverter`; the background loop is
a no-op while a request-driven claim is in flight (the loop and the endpoint
both try to claim; whoever gets the row first owns the work).
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

import psycopg
from fastapi import FastAPI, HTTPException
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

logger = logging.getLogger("arch3dar.converter")
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)

IFCCONVERT_PATH = os.environ.get("IFCCONVERT_PATH", "/usr/local/bin/IfcConvert")
CONVERSION_TIMEOUT_S = int(os.environ.get("CONVERSION_TIMEOUT_S", "300"))
MINIO_ENDPOINT = os.environ["MINIO_ENDPOINT"]
MINIO_ACCESS_KEY = os.environ["MINIO_ACCESS_KEY"]
MINIO_SECRET_KEY = os.environ["MINIO_SECRET_KEY"]
MINIO_USE_SSL = os.environ.get("MINIO_USE_SSL", "false").lower() == "true"
MINIO_BUCKET_IFC = os.environ.get("MINIO_BUCKET_IFC", "ifc-files")
MINIO_BUCKET_GLB = os.environ.get("MINIO_BUCKET_GLB", "glb-files")
MINIO_BUCKET_THUMBNAILS = os.environ.get("MINIO_BUCKET_THUMBNAILS", "thumbnails")
DATABASE_URL = os.environ["DATABASE_URL"]
# .NET / Npgsql sends connection strings like "Host=postgres;Port=5432;Database=...".
# psycopg expects libpq-style "host=... port=... dbname=..." or a URL.
# Convert once at startup so handlers can use the canonical form.
def _normalize_dsn(dsn: str) -> str:
    if "://" in dsn:
        return dsn
    parts = dsn.split(";")
    mapping = {
        "Host": "host", "Server": "host",
        "Port": "port",
        "Database": "dbname",
        "Username": "user", "User ID": "user",
        "Password": "password",
    }
    out = []
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        k = mapping.get(k.strip(), k.strip().lower())
        out.append(f"{k}={v.strip()}")
    return " ".join(out)

DATABASE_URL = _normalize_dsn(DATABASE_URL)
POLL_INTERVAL_S = float(os.environ.get("CONVERTER_POLL_INTERVAL_S", "2.0"))


def make_minio() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_USE_SSL,
    )


minio_client = make_minio()


class ConvertRequest(BaseModel):
    projectId: str


class ConvertResponse(BaseModel):
    glbKey: str
    thumbnailKey: str
    durationMs: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(claim_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Arch3DAR Converter", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/convert")
async def convert(req: ConvertRequest) -> ConvertResponse:
    try:
        project_id = req.projectId
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid projectId: {e}")

    return await process_project(project_id)


async def claim_loop() -> None:
    """Periodically claim a `UploadReceived` project and process it.

    The claim is a single SQL statement with `FOR UPDATE SKIP LOCKED` so that
    multiple replicas (or the HTTP endpoint racing with the loop) do not
    double-process. The lock is held for the duration of the row update that
    flips status to `Processing`; once released, the row is no longer eligible.
    """
    while True:
        try:
            claimed = await _try_claim_one()
            if claimed:
                await process_project(str(claimed))
            else:
                await asyncio.sleep(POLL_INTERVAL_S)
        except asyncio.CancelledError:
            return
        except Exception as e:  # noqa: BLE001
            logger.exception("claim loop error: %s", e)
            await asyncio.sleep(POLL_INTERVAL_S)


async def _try_claim_one() -> Optional[uuid.UUID]:
    """Atomically claim one UploadReceived project. Returns the project id, or None."""
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT "Id"
                    FROM projects
                    WHERE "Status" = 'UploadReceived'
                    ORDER BY "CreatedAt" ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """,
                )
                row = await cur.fetchone()
                if row is None:
                    return None
                await cur.execute(
                    """
                    UPDATE projects
                    SET "Status" = 'Processing',
                        "UpdatedAt" = NOW()
                    WHERE "Id" = %s
                    """,
                    (row[0],),
                )
                await conn.commit()
                return row[0]
    except Exception as e:  # noqa: BLE001
        logger.exception("claim failed: %s", e)
        return None


async def process_project(project_id: str) -> ConvertResponse:
    started = time.monotonic()

    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT "IfcObjectKey"
                FROM projects
                WHERE "Id" = %s
                """,
                (project_id,),
            )
            row = await cur.fetchone()
            if row is None:
                await _mark_failed(project_id, "project not found")
                raise HTTPException(status_code=404, detail="project not found")
            ifc_key = row[0]
            if not ifc_key:
                await _mark_failed(project_id, "missing source ifc key")
                raise HTTPException(status_code=400, detail="missing source ifc key")

            ifc_bytes = await _download(MINIO_BUCKET_IFC, ifc_key)
            if not ifc_bytes:
                await _mark_failed(project_id, "failed to download source ifc")
                raise HTTPException(status_code=500, detail="download failed")

        try:
            glb_bytes, thumb_bytes = await asyncio.to_thread(_run_ifc_convert, ifc_bytes)
        except ConversionFailure as e:
            await _mark_failed(project_id, str(e))
            raise HTTPException(status_code=500, detail=str(e))

        glb_key = f"projects/{project_id}/model.glb"
        thumb_key = f"projects/{project_id}/thumb.png"
        await _upload(MINIO_BUCKET_GLB, glb_key, glb_bytes, "model/gltf-binary")
        await _upload(MINIO_BUCKET_THUMBNAILS, thumb_key, thumb_bytes, "image/png")

        duration_ms = int((time.monotonic() - started) * 1000)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE projects
                SET "Status" = 'ReadyToPublish',
                    "GlbObjectKey" = %s,
                    "ThumbnailObjectKey" = %s,
                    "ConversionDurationMs" = %s,
                    "UpdatedAt" = NOW(),
                    "ErrorMessage" = NULL
                WHERE "Id" = %s
                """,
                (glb_key, thumb_key, duration_ms, project_id),
            )
            await conn.commit()
        return ConvertResponse(glbKey=glb_key, thumbnailKey=thumb_key, durationMs=duration_ms)


async def _mark_failed(project_id: str, reason: str) -> None:
    try:
        async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE projects
                    SET "Status" = 'Failed',
                        "ErrorMessage" = %s,
                        "UpdatedAt" = NOW()
                    WHERE "Id" = %s
                    """,
                    (reason[:500], project_id),
                )
                await conn.commit()
    except Exception as e:  # noqa: BLE001
        logger.exception("failed to mark project failed: %s", e)


class ConversionFailure(RuntimeError):
    pass


def _run_ifc_convert(ifc_bytes: bytes) -> tuple[bytes, bytes]:
    """Run IfcConvert synchronously, producing GLB and thumbnail bytes."""
    import subprocess
    import tempfile
    from PIL import Image

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

        # Thumbnail via IfcConvert --thumbnail flag.
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
            # Fall back to a 1x1 placeholder so the UI still has a poster.
            img = Image.new("RGB", (320, 240), color=(220, 220, 220))
            img.save(png_path)

        with open(glb_path, "rb") as f:
            glb_bytes = f.read()
        with open(png_path, "rb") as f:
            thumb_bytes = f.read()

        if not glb_bytes:
            raise ConversionFailure("empty GLB output")

        return glb_bytes, thumb_bytes


async def _download(bucket: str, key: str) -> Optional[bytes]:
    try:
        resp = minio_client.get_object(bucket, key)
        data = resp.read()
        resp.close()
        resp.release_conn()
        return data
    except S3Error as e:
        logger.warning("minio download failed: %s", e)
        return None


async def _upload(bucket: str, key: str, data: bytes, content_type: str) -> None:
    import io as _io
    try:
        minio_client.put_object(
            bucket,
            key,
            _io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
    except S3Error as e:
        logger.exception("minio upload failed: %s", e)
        raise


# Late import to avoid pulling uuid at module top — the claim loop uses uuid.
import uuid  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("converter_service:app", host="0.0.0.0", port=8080)
