"""Tests for Sharing endpoints + public viewer — open access."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.identity import DEFAULT_OWNER_ID
from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat
from app.features.projects.models import Project
from app.features.sharing.models import ShareLink


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
) -> ConversionJob:
    job = ConversionJob(
        id=str(uuid.uuid4()),
        model_file_id=model_file_id,
        status=status,
        attempts=1,
        glb_storage_key=f"converted/test/{model_file_id}.glb",
        qr_storage_key=f"qr/test/{model_file_id}.png",
        duration_ms=5000,
    )
    session.add(job)
    session.flush()
    return job


class TestCreateShareLink:
    def test_create_share_link_success(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        response = client.post(f"/api/v1/files/{model_file.id}/share")

        assert response.status_code == 201
        data = response.json()
        assert "share_id" in data
        assert "token" in data
        assert len(data["token"]) == 64
        assert data["public_url"].startswith("http")
        assert "/s/" in data["public_url"]

    def test_create_share_link_404_for_nonexistent_file(
        self, client: TestClient,
    ) -> None:
        fake_id = uuid.uuid4()
        response = client.post(f"/api/v1/files/{fake_id}/share")
        assert response.status_code == 404

    def test_create_share_link_409_when_not_ready(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.pending)
        db_session.commit()

        response = client.post(f"/api/v1/files/{model_file.id}/share")
        assert response.status_code == 409


class TestListShareLinks:
    def test_list_shares_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/shares")
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_list_shares_returns_created_links(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        client.post(f"/api/v1/files/{model_file.id}/share")

        response = client.get("/api/v1/shares")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["model_file_id"] == str(model_file.id)


class TestRevokeShareLink:
    def test_revoke_share_success(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        create_resp = client.post(f"/api/v1/files/{model_file.id}/share")
        share_id = create_resp.json()["share_id"]

        response = client.delete(f"/api/v1/shares/{share_id}")
        assert response.status_code == 204

    def test_revoke_share_404_for_nonexistent(self, client: TestClient) -> None:
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/v1/shares/{fake_id}")
        assert response.status_code == 404


class TestPublicManifest:
    def test_manifest_returns_metadata(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        create_resp = client.post(f"/api/v1/files/{model_file.id}/share")
        token = create_resp.json()["token"]

        response = client.get(f"/s/{token}/manifest")
        assert response.status_code == 200
        data = response.json()
        assert data["model_file_id"] == str(model_file.id)
        assert data["filename"] == "test-model.ifc"
        assert data["source_format"] == "ifc"
        assert data["status"] == "ready"
        assert "model.glb" in data["glb_url"]

    def test_manifest_404_for_invalid_token(self, client: TestClient) -> None:
        response = client.get("/s/invalidtoken123/manifest")
        assert response.status_code == 404

    def test_manifest_404_for_revoked_token(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        create_resp = client.post(f"/api/v1/files/{model_file.id}/share")
        share_id = create_resp.json()["share_id"]
        token = create_resp.json()["token"]

        client.delete(f"/api/v1/shares/{share_id}")

        response = client.get(f"/s/{token}/manifest")
        assert response.status_code == 404


class TestPublicGlb:
    def test_glb_serves_binary(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project = _create_test_project(db_session)
        model_file = _create_test_model_file(db_session, project.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)

        glb_dir = FIXED_STORAGE_ROOT / "converted" / "test"
        glb_dir.mkdir(parents=True, exist_ok=True)
        glb_path = glb_dir / f"{model_file.id}.glb"
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)
        job.glb_storage_key = f"converted/test/{model_file.id}.glb"
        db_session.commit()

        create_resp = client.post(f"/api/v1/files/{model_file.id}/share")
        token = create_resp.json()["token"]

        response = client.get(f"/s/{token}/model.glb")
        assert response.status_code == 200
        assert response.headers["content-type"] == "model/gltf-binary"

    def test_glb_404_for_invalid_token(self, client: TestClient) -> None:
        response = client.get("/s/invalidtoken123/model.glb")
        assert response.status_code == 404
