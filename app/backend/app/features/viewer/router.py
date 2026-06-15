"""FastAPI routes for public share viewing (no auth required).

Endpoints (public, token-authenticated):
    GET  /s/{token}/manifest       — share manifest (metadata)
    GET  /s/{token}/model.glb      — GLB binary
    GET  /s/{token}/model.usdz     — USDZ binary (iOS Quick Look)
    GET  /s/{token}/qr.png         — QR code PNG
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import NotFoundError
from app.core.storage.local_disk import LocalDiskStorage
from app.features.models.models import ConversionJob, JobStatus, ModelFile
from app.features.sharing import service
from app.features.sharing.schemas import PublicShareManifest

router = APIRouter(tags=["public-share"])


def _resolve_share(token: str, db: Session):
    share = service.resolve_token(db, token=token)
    if share is None:
        raise NotFoundError("Share link not found or has been revoked.")
    return share


def _get_ready_job(db: Session, model_file_id: str):
    job = db.scalar(
        select(ConversionJob)
        .where(ConversionJob.model_file_id == model_file_id)
        .where(ConversionJob.status == JobStatus.ready)
        .order_by(ConversionJob.created_at.desc())
        .limit(1)
    )
    return job


@router.get("/s/{token}/manifest", response_model=PublicShareManifest)
def get_share_manifest(
    token: str,
    db: Session = Depends(get_db),
) -> PublicShareManifest:
    share = _resolve_share(token, db)

    model_file = db.get(ModelFile, share.model_file_id)
    if model_file is None:
        raise NotFoundError("Model file not found.")

    job = _get_ready_job(db, share.model_file_id)
    if job is None:
        raise NotFoundError("Model is not ready for viewing.")

    base = f"/s/{token}"
    return PublicShareManifest(
        model_file_id=model_file.id,
        filename=model_file.original_filename,
        source_format=model_file.source_format.value,
        status="ready",
        glb_url=f"{base}/model.glb",
        usdz_url=f"{base}/model.usdz" if job.usdz_storage_key else None,
        qr_url=f"{base}/qr.png",
    )


@router.get("/s/{token}/model.glb")
def get_share_glb(
    token: str,
    db: Session = Depends(get_db),
) -> Response:
    share = _resolve_share(token, db)

    job = _get_ready_job(db, share.model_file_id)
    if job is None or job.glb_storage_key is None:
        raise NotFoundError("GLB not available.")

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    try:
        with storage.open_for_read(job.glb_storage_key) as f:
            glb_data = f.read()
        return Response(
            content=glb_data,
            media_type="model/gltf-binary",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Accept-Ranges": "bytes",
            },
        )
    except Exception:
        raise NotFoundError("GLB file not found in storage.")


@router.get("/s/{token}/model.usdz")
def get_share_usdz(
    token: str,
    db: Session = Depends(get_db),
) -> Response:
    share = _resolve_share(token, db)

    job = _get_ready_job(db, share.model_file_id)
    if job is None or job.usdz_storage_key is None:
        raise NotFoundError("USDZ not available.")

    settings = get_settings()
    storage = LocalDiskStorage(settings.STORAGE_ROOT)

    try:
        with storage.open_for_read(job.usdz_storage_key) as f:
            usdz_data = f.read()
        return Response(
            content=usdz_data,
            media_type="model/usd",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception:
        raise NotFoundError("USDZ file not found in storage.")


@router.get("/s/{token}/qr.png")
def get_share_qr(
    token: str,
    db: Session = Depends(get_db),
) -> Response:
    share = _resolve_share(token, db)

    job = _get_ready_job(db, share.model_file_id)
    if job is None:
        raise NotFoundError("Model is not ready for viewing.")

    # Generate the QR on the fly — it encodes the public share URL, which only
    # exists once the share is created (no token at conversion time).
    import io

    import segno

    settings = get_settings()
    url = f"{settings.PUBLIC_BASE_URL}/s/{token}"
    buf = io.BytesIO()
    segno.make(url).save(buf, kind="png", scale=8, border=2)
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
