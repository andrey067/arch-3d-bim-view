"""Tests for Sprint 5 — Sharing endpoints + public viewer.

Tests:
- POST /api/v1/files/{id}/share — create share link
- GET  /api/v1/shares — list share links
- DELETE /api/v1/shares/{id} — revoke share link
- GET  /s/{token}/manifest — public manifest
- GET  /s/{token}/model.glb — public GLB
- GET  /s/{token}/thumbnail.webp — public thumbnail
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat
from app.features.projects.models import Project
from app.features.auth.models import User
from app.features.sharing.models import ShareLink


FIXED_STORAGE_ROOT = Path("/tmp/test-storage-arch3dar")


def _create_test_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="$2b$12$test_hash_placeholder",
        display_name="Test User",
    )
    session.add(user)
    session.flush()
    return user


def _create_test_project(session: Session, owner_id: uuid.UUID) -> Project:
    project = Project(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name="Test Project",
        description="A test project",
    )
    session.add(project)
    session.flush()
    return project


def _create_test_model_file(
    session: Session,
    project_id: uuid.UUID,
    uploader_id: uuid.UUID,
) -> ModelFile:
    model_file = ModelFile(
        id=uuid.uuid4(),
        project_id=project_id,
        uploader_id=uploader_id,
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
    model_file_id: uuid.UUID,
    status: JobStatus = JobStatus.ready,
) -> ConversionJob:
    job = ConversionJob(
        id=uuid.uuid4(),
        model_file_id=model_file_id,
        status=status,
        attempts=1,
        glb_storage_key=f"converted/test/{model_file_id}.glb",
        thumbnail_storage_key=f"thumbnails/test/{model_file_id}.webp",
        duration_ms=5000,
    )
    session.add(job)
    session.flush()
    return job


def _get_auth_header(client: TestClient, email: str = "test@example.com", password: str = "password123") -> dict[str, str]:
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ #
#  Create Share Link                                                  #
# ------------------------------------------------------------------ #

class TestCreateShareLink:
    """Tests for POST /api/v1/files/{id}/share."""

    def test_create_share_link_success(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Creating a share link returns share_id, token, and public_url."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        response = client.post(
            f"/api/v1/files/{model_file.id}/share",
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "share_id" in data
        assert "token" in data
        assert len(data["token"]) == 64  # 32 bytes hex
        assert data["public_url"].startswith("http")
        assert "/s/" in data["public_url"]

    def test_create_share_link_requires_auth(
        self,
        client: TestClient,
    ) -> None:
        """Creating a share link requires authentication."""
        file_id = uuid.uuid4()
        response = client.post(f"/api/v1/files/{file_id}/share")
        assert response.status_code in (401, 422)

    def test_create_share_link_404_for_nonexistent_file(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 404 for non-existent model file."""
        headers = _get_auth_header(client)
        fake_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/files/{fake_id}/share",
            headers=headers,
        )
        assert response.status_code == 404

    def test_create_share_link_409_when_not_ready(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 409 when conversion is not ready."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.pending)
        db_session.commit()

        response = client.post(
            f"/api/v1/files/{model_file.id}/share",
            headers=headers,
        )
        assert response.status_code == 409

    def test_create_share_link_forbidden_for_other_user(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 403 when user doesn't own the project."""
        headers = _get_auth_header(client, email="owner@example.com")
        owner = db_session.query(User).filter(User.email == "owner@example.com").first()
        assert owner is not None

        # Create another user
        other = _create_test_user(db_session)
        project = _create_test_project(db_session, other.id)
        model_file = _create_test_model_file(db_session, project.id, other.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        response = client.post(
            f"/api/v1/files/{model_file.id}/share",
            headers=headers,
        )
        assert response.status_code == 403


# ------------------------------------------------------------------ #
#  List Share Links                                                   #
# ------------------------------------------------------------------ #

class TestListShareLinks:
    """Tests for GET /api/v1/shares."""

    def test_list_shares_empty(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns empty list when no shares exist."""
        headers = _get_auth_header(client)

        response = client.get("/api/v1/shares", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_list_shares_returns_created_links(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Lists share links created by the user."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        # Create a share link
        client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)

        response = client.get("/api/v1/shares", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["model_file_id"] == str(model_file.id)
        assert item["revoked_at"] is None
        # Token should NOT be in the list response
        assert "token" not in item

    def test_list_shares_requires_auth(
        self,
        client: TestClient,
    ) -> None:
        """Listing shares requires authentication."""
        response = client.get("/api/v1/shares")
        assert response.status_code in (401, 422)


# ------------------------------------------------------------------ #
#  Revoke Share Link                                                  #
# ------------------------------------------------------------------ #

class TestRevokeShareLink:
    """Tests for DELETE /api/v1/shares/{id}."""

    def test_revoke_share_success(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Revoking a share link returns 204."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        # Create share
        create_resp = client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)
        share_id = create_resp.json()["share_id"]

        # Revoke
        response = client.delete(f"/api/v1/shares/{share_id}", headers=headers)
        assert response.status_code == 204

    def test_revoke_share_idempotent(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Revoking an already-revoked share is idempotent (204)."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        create_resp = client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)
        share_id = create_resp.json()["share_id"]

        # Revoke twice
        client.delete(f"/api/v1/shares/{share_id}", headers=headers)
        response = client.delete(f"/api/v1/shares/{share_id}", headers=headers)
        assert response.status_code == 204

    def test_revoke_share_404_for_nonexistent(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 404 for non-existent share."""
        headers = _get_auth_header(client)
        fake_id = uuid.uuid4()

        response = client.delete(f"/api/v1/shares/{fake_id}", headers=headers)
        assert response.status_code == 404

    def test_revoke_share_forbidden_for_other_user(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 403 when user doesn't own the project."""
        # Create as owner
        owner_headers = _get_auth_header(client, email="owner@example.com")
        owner = db_session.query(User).filter(User.email == "owner@example.com").first()
        assert owner is not None

        other = _create_test_user(db_session)
        project = _create_test_project(db_session, other.id)
        model_file = _create_test_model_file(db_session, project.id, other.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        # Create share as other user directly in DB
        share = ShareLink(
            id=uuid.uuid4(),
            token="a" * 64,
            project_id=project.id,
            model_file_id=model_file.id,
            created_by=other.id,
        )
        db_session.add(share)
        db_session.commit()

        # Try to revoke as owner (who doesn't own this project)
        response = client.delete(f"/api/v1/shares/{share.id}", headers=owner_headers)
        assert response.status_code == 403


# ------------------------------------------------------------------ #
#  Public Viewer — Manifest                                           #
# ------------------------------------------------------------------ #

class TestPublicManifest:
    """Tests for GET /s/{token}/manifest."""

    def test_manifest_returns_metadata(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Public manifest returns model metadata."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        # Create share
        create_resp = client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)
        token = create_resp.json()["token"]

        # Fetch manifest (no auth)
        response = client.get(f"/s/{token}/manifest")
        assert response.status_code == 200
        data = response.json()
        assert data["model_file_id"] == str(model_file.id)
        assert data["filename"] == "test-model.ifc"
        assert data["source_format"] == "ifc"
        assert data["status"] == "ready"
        assert "model.glb" in data["glb_url"]
        assert "thumbnail.webp" in data["thumbnail_url"]

    def test_manifest_404_for_invalid_token(
        self,
        client: TestClient,
    ) -> None:
        """Returns 404 for invalid token."""
        response = client.get("/s/invalidtoken123/manifest")
        assert response.status_code == 404

    def test_manifest_404_for_revoked_token(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Returns 404 for revoked share link."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        create_resp = client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)
        share_id = create_resp.json()["share_id"]
        token = create_resp.json()["token"]

        # Revoke
        client.delete(f"/api/v1/shares/{share_id}", headers=headers)

        # Try to access manifest
        response = client.get(f"/s/{token}/manifest")
        assert response.status_code == 404


# ------------------------------------------------------------------ #
#  Public Viewer — GLB                                                #
# ------------------------------------------------------------------ #

class TestPublicGlb:
    """Tests for GET /s/{token}/model.glb."""

    def test_glb_serves_binary(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Public GLB endpoint serves the binary file."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)

        # Create fake GLB in storage
        glb_dir = FIXED_STORAGE_ROOT / "converted" / "test"
        glb_dir.mkdir(parents=True, exist_ok=True)
        glb_path = glb_dir / f"{model_file.id}.glb"
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)
        job.glb_storage_key = f"converted/test/{model_file.id}.glb"
        db_session.commit()

        # Create share
        create_resp = client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)
        token = create_resp.json()["token"]

        # Fetch GLB (no auth)
        response = client.get(f"/s/{token}/model.glb")
        assert response.status_code == 200
        assert response.headers["content-type"] == "model/gltf-binary"
        assert "cache-control" in response.headers

    def test_glb_404_for_invalid_token(
        self,
        client: TestClient,
    ) -> None:
        """Returns 404 for invalid token."""
        response = client.get("/s/invalidtoken123/model.glb")
        assert response.status_code == 404


# ------------------------------------------------------------------ #
#  Public Viewer — Thumbnail                                          #
# ------------------------------------------------------------------ #

class TestPublicThumbnail:
    """Tests for GET /s/{token}/thumbnail.webp."""

    def test_thumbnail_serves_webp(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Public thumbnail endpoint serves WebP image."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)

        # Create fake thumbnail in storage
        thumb_dir = FIXED_STORAGE_ROOT / "thumbnails" / "test"
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{model_file.id}.webp"
        thumb_path.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100)
        job.thumbnail_storage_key = f"thumbnails/test/{model_file.id}.webp"
        db_session.commit()

        # Create share
        create_resp = client.post(f"/api/v1/files/{model_file.id}/share", headers=headers)
        token = create_resp.json()["token"]

        # Fetch thumbnail (no auth)
        response = client.get(f"/s/{token}/thumbnail.webp")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert "cache-control" in response.headers

    def test_thumbnail_404_for_invalid_token(
        self,
        client: TestClient,
    ) -> None:
        """Returns 404 for invalid token."""
        response = client.get("/s/invalidtoken123/thumbnail.webp")
        assert response.status_code == 404
