"""Tests for Sprint 4 — Viewer endpoints (thumbnail, viewer metadata, GLB serving).

Tests the authenticated endpoints for viewing converted models:
- GET /api/v1/files/{id}/thumbnail
- GET /api/v1/files/{id}/viewer
- GET /api/v1/files/{id}/glb
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat
from app.features.projects.models import Project
from app.features.auth.models import User


FIXED_STORAGE_ROOT = Path("/tmp/test-storage-arch3dar")


def _create_test_user(session: Session) -> User:
    """Create a test user and return it."""
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
    """Create a test project and return it."""
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
    """Create a test model file and return it."""
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
    glb_key: str | None = None,
    thumb_key: str | None = None,
) -> ConversionJob:
    """Create a test conversion job and return it."""
    job = ConversionJob(
        id=uuid.uuid4(),
        model_file_id=model_file_id,
        status=status,
        attempts=1,
        glb_storage_key=glb_key or f"converted/test/{model_file_id}.glb",
        thumbnail_storage_key=thumb_key or f"thumbnails/test/{model_file_id}.webp",
        duration_ms=5000,
    )
    session.add(job)
    session.flush()
    return job


def _get_auth_header(client: TestClient, email: str = "test@example.com", password: str = "password123") -> dict[str, str]:
    """Get auth header by registering and logging in."""
    # Register
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestViewerEndpoint:
    """Tests for GET /api/v1/files/{id}/viewer."""

    def test_viewer_returns_metadata_when_ready(
        self,
        client: TestClient,
        db_session: Session,
        tmp_storage: Path,
    ) -> None:
        """Viewer endpoint returns metadata for a ready conversion."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/viewer",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model_file_id"] == str(model_file.id)
        assert data["status"] == "ready"
        assert data["glb_url"] is not None
        assert data["thumbnail_url"] is not None
        assert data["filename"] == "test-model.ifc"

    def test_viewer_returns_pending_status(
        self,
        client: TestClient,
        db_session: Session,
        tmp_storage: Path,
    ) -> None:
        """Viewer endpoint returns pending status when conversion not started."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.pending)
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/viewer",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["glb_url"] is None
        assert data["thumbnail_url"] is None

    def test_viewer_returns_failed_status_with_error(
        self,
        client: TestClient,
        db_session: Session,
        tmp_storage: Path,
    ) -> None:
        """Viewer endpoint returns failed status with error message."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.failed)
        job.last_error = "Blender render failed"
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/viewer",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["last_error"] == "Blender render failed"

    def test_viewer_requires_auth(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Viewer endpoint requires authentication."""
        model_id = uuid.uuid4()
        response = client.get(f"/api/v1/files/{model_id}/viewer")
        assert response.status_code in (401, 422)

    def test_viewer_returns_404_for_nonexistent_file(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Viewer endpoint returns 404 for non-existent file."""
        headers = _get_auth_header(client)
        fake_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/files/{fake_id}/viewer",
            headers=headers,
        )

        assert response.status_code == 404


class TestThumbnailEndpoint:
    """Tests for GET /api/v1/files/{id}/thumbnail."""

    def test_thumbnail_serves_webp_when_ready(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Thumbnail endpoint serves WebP image when conversion is ready."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)

        # Create a fake thumbnail file using the fixed storage root
        thumb_dir = FIXED_STORAGE_ROOT / "thumbnails" / str(project.id)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / f"{model_file.id}.webp"
        # Write minimal WebP header (RIFF....WEBP)
        thumb_path.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100)
        job.thumbnail_storage_key = f"thumbnails/{project.id}/{model_file.id}.webp"
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/thumbnail",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert "cache-control" in response.headers

    def test_thumbnail_returns_404_when_not_ready(
        self,
        client: TestClient,
        db_session: Session,
        tmp_storage: Path,
    ) -> None:
        """Thumbnail endpoint returns 404 when conversion not ready."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.pending)
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/thumbnail",
            headers=headers,
        )

        assert response.status_code == 404

    def test_thumbnail_requires_auth(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """Thumbnail endpoint requires authentication."""
        model_id = uuid.uuid4()
        response = client.get(f"/api/v1/files/{model_id}/thumbnail")
        assert response.status_code in (401, 422)


class TestGlbEndpoint:
    """Tests for GET /api/v1/files/{id}/glb."""

    def test_glb_serves_binary_when_ready(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """GLB endpoint serves binary file when conversion is ready."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        job = _create_test_conversion_job(db_session, model_file.id, JobStatus.ready)

        # Create a fake GLB file using the fixed storage root
        glb_dir = FIXED_STORAGE_ROOT / "converted" / str(project.id)
        glb_dir.mkdir(parents=True, exist_ok=True)
        glb_path = glb_dir / f"{model_file.id}.glb"
        # Write minimal GLB header (glTF)
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)
        job.glb_storage_key = f"converted/{project.id}/{model_file.id}.glb"
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/glb",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "model/gltf-binary"
        assert "cache-control" in response.headers
        assert "accept-ranges" in response.headers

    def test_glb_returns_404_when_not_ready(
        self,
        client: TestClient,
        db_session: Session,
        tmp_storage: Path,
    ) -> None:
        """GLB endpoint returns 404 when conversion not ready."""
        headers = _get_auth_header(client)
        user = db_session.query(User).first()
        assert user is not None

        project = _create_test_project(db_session, user.id)
        model_file = _create_test_model_file(db_session, project.id, user.id)
        _create_test_conversion_job(db_session, model_file.id, JobStatus.running)
        db_session.commit()

        response = client.get(
            f"/api/v1/files/{model_file.id}/glb",
            headers=headers,
        )

        assert response.status_code == 404

    def test_glb_requires_auth(
        self,
        client: TestClient,
        db_session: Session,
    ) -> None:
        """GLB endpoint requires authentication."""
        model_id = uuid.uuid4()
        response = client.get(f"/api/v1/files/{model_id}/glb")
        assert response.status_code in (401, 422)


class TestThumbnailPipeline:
    """Tests for the thumbnail generation pipeline (mocked Blender)."""

    @patch("app.features.conversion.pipelines.thumbnail.subprocess.run")
    def test_render_produces_webp(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Thumbnail render produces a valid WebP file."""
        from app.features.conversion.pipelines.thumbnail import render

        # Create a fake GLB input
        glb_path = tmp_path / "input.glb"
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)

        # Create output path
        output_path = tmp_path / "output.webp"

        # Mock Blender to create the output file
        def side_effect(args, **kwargs):
            # Simulate Blender creating the output file
            output_path.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100)
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        # Render thumbnail
        render(glb_path, output_path, size=(800, 600))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Verify WebP header
        with open(output_path, "rb") as f:
            header = f.read(12)
            assert header[:4] == b"RIFF"
            assert header[8:12] == b"WEBP"

    @patch("app.features.conversion.pipelines.thumbnail.subprocess.run")
    def test_render_raises_on_blender_failure(
        self,
        mock_run: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Thumbnail render raises ConversionError on Blender failure."""
        from app.features.conversion.pipelines.common import ConversionError
        from app.features.conversion.pipelines.thumbnail import render

        glb_path = tmp_path / "input.glb"
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)

        output_path = tmp_path / "output.webp"

        # Mock Blender failure
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: failed to render",
        )

        with pytest.raises(ConversionError, match="Blender thumbnail render failed"):
            render(glb_path, output_path, size=(800, 600))

    def test_render_raises_on_missing_input(
        self,
        tmp_path: Path,
    ) -> None:
        """Thumbnail render raises ConversionError on missing input file."""
        from app.features.conversion.pipelines.common import ConversionError
        from app.features.conversion.pipelines.thumbnail import render

        glb_path = tmp_path / "nonexistent.glb"
        output_path = tmp_path / "output.webp"

        with pytest.raises(ConversionError, match="GLB file not found"):
            render(glb_path, output_path, size=(800, 600))

    def test_render_raises_on_invalid_size(
        self,
        tmp_path: Path,
    ) -> None:
        """Thumbnail render raises ConversionError on invalid size."""
        from app.features.conversion.pipelines.common import ConversionError
        from app.features.conversion.pipelines.thumbnail import render

        glb_path = tmp_path / "input.glb"
        glb_path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)

        output_path = tmp_path / "output.webp"

        with pytest.raises(ConversionError, match="Invalid thumbnail size"):
            render(glb_path, output_path, size=(0, 600))
