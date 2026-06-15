"""Tests for Viewer endpoints — open access."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.identity import DEFAULT_OWNER_ID
from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat
from app.features.projects.models import Project


FIXED_STORAGE_ROOT = Path("/tmp/test-storage-arch3dar")


def _create_test_project(session: Session) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        owner_id=DEFAULT_OWNER_ID,
        name="Test Project",
        description="A test project",
    )
    session.add(project)
    session.flush()
    return project


def _create_test_model_file(session: Session, project_id: str) -> ModelFile:
    model_file = ModelFile(
        id=str(uuid.uuid4()),
        project_id=project_id,
        uploader_id=DEFAULT_OWNER_ID,
        original_filename="test-model.ifc",
        source_format=SourceFormat.ifc,
        size_bytes=1024,
        original_storage_key=f"originals/{project_id}/test.ifc",
        content_hash="a" * 64,
    )
    session.add(model_file)
    session.flush()
    return model_file


def _create_test_conversion_job(
    session: Session,
    model_file_id: str,
    status: JobStatus = JobStatus.ready,
    glb_key: str | None = None,
) -> ConversionJob:
    job = ConversionJob(
        id=str(uuid.uuid4()),
        model_file_id=model_file_id,
        status=status,
        attempts=1,
        glb_storage_key=glb_key or f"converted/test/{model_file_id}.glb",
        duration_ms=5000,
    )
    session.add(job)
    session.flush()
    return job


class TestViewerEndpoint:
    def test_viewer_returns_metadata_when_ready(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        response = client.get(f"/api/v1/files/{model_file.id}/viewer")

        assert response.status_code == 200
        data = response.json()
        assert data["model_file_id"] == str(model_file.id)
        assert data["status"] == "ready"
        assert data["glb_url"] is not None
        assert data["filename"] == "test-model.ifc"

    def test_viewer_returns_pending_status(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.pending)
        db_session.commit()

        response = client.get(f"/api/v1/files/{model_file.id}/viewer")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["glb_url"] is None

    def test_viewer_returns_failed_status_with_error(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.failed)
        job.last_error = "Pipeline failed"
        db_session.commit()

        response = client.get(f"/api/v1/files/{model_file.id}/viewer")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["last_error"] == "Pipeline failed"

    def test_viewer_returns_404_for_nonexistent_file(self, client: TestClient) -> None:
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/files/{fake_id}/viewer")
        assert response.status_code == 404


class TestGlbEndpoint:
    def test_glb_serves_binary_when_ready(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)

        glb_dir = FIXED_STORAGE_ROOT / "converted" / str(project.id)
        glb_dir.mkdir(parents=True, exist_ok=True)
        glb_path = glb_dir / f"{model_file.id}.glb"
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)
        job.glb_storage_key = f"converted/{project.id}/{model_file.id}.glb"
        db_session.commit()

        response = client.get(f"/api/v1/files/{model_file.id}/glb")

        assert response.status_code == 200
        assert response.headers["content-type"] == "model/gltf-binary"
        assert "cache-control" in response.headers
        assert "accept-ranges" in response.headers

    def test_glb_returns_404_when_not_ready(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.running)
        db_session.commit()

        response = client.get(f"/api/v1/files/{model_file.id}/glb")
        assert response.status_code == 404
