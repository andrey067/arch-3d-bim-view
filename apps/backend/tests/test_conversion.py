"""Tests for VS-Conversion: job creation, status, retry, and pipeline dispatch."""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GLB_MAGIC = b"glTF" + b"\x02\x00\x00\x00" + b"\x00\x00\x00\x00"


def _create_project(client: TestClient, token: str) -> str:
    """Create a project and return its ID."""
    resp = client.post(
        "/api/v1/projects",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _register_and_login(client: TestClient) -> str:
    """Register a user and return the access token."""
    email = f"conv_{uuid.uuid4().hex[:8]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _upload_glb(client: TestClient, token: str, project_id: str) -> dict:
    """Upload a minimal GLB file and return the response."""
    content = GLB_MAGIC + b"\x00" * 100
    resp = client.post(
        f"/api/v1/projects/{project_id}/files",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("test.glb", content, "model/gltf-binary")},
    )
    assert resp.status_code == 202
    return resp.json()


# ---------------------------------------------------------------------------
# Tests: Upload creates ConversionJob
# ---------------------------------------------------------------------------


class TestUploadCreatesJob:
    """Verify that uploading a file also creates a ConversionJob."""

    def test_upload_returns_conversion_job_id(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)

        assert "conversion_job_id" in result
        assert result["status"] == "pending"
        assert result["conversion_job_id"] is not None

    def test_conversion_job_persisted(self, client: TestClient, db_session: Session) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)

        job_id = uuid.UUID(result["conversion_job_id"])
        job = db_session.get(ConversionJob, job_id)
        assert job is not None
        assert job.status == JobStatus.pending
        assert job.attempts == 0


# ---------------------------------------------------------------------------
# Tests: Job status endpoint (T036)
# ---------------------------------------------------------------------------


class TestJobStatusEndpoint:
    """Tests for GET /api/v1/jobs/{job_id}."""

    def test_get_pending_job(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)
        job_id = result["conversion_job_id"]

        resp = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["attempts"] == 0
        assert data["last_error"] is None

    def test_job_not_found(self, client: TestClient) -> None:
        token = _register_and_login(client)
        fake_id = str(uuid.uuid4())
        resp = client.get(
            f"/api/v1/jobs/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_job_forbidden_other_user(self, client: TestClient) -> None:
        token1 = _register_and_login(client)
        project_id = _create_project(client, token1)
        result = _upload_glb(client, token1, project_id)
        job_id = result["conversion_job_id"]

        # Create a second user
        token2 = _register_and_login(client)
        resp = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Tests: Job retry endpoint (T037)
# ---------------------------------------------------------------------------


class TestJobRetryEndpoint:
    """Tests for POST /api/v1/jobs/{job_id}/retry."""

    def test_retry_pending_job_returns_409(self, client: TestClient) -> None:
        """Cannot retry a job that hasn't failed yet."""
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)
        job_id = result["conversion_job_id"]

        resp = client.post(
            f"/api/v1/jobs/{job_id}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    def test_retry_failed_job_resets_to_pending(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Retrying a failed job resets it to pending."""
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)
        job_id = uuid.UUID(result["conversion_job_id"])

        # Manually mark job as failed
        job = db_session.get(ConversionJob, job_id)
        assert job is not None
        job.status = JobStatus.failed
        job.last_error = "Test error"
        db_session.flush()

        resp = client.post(
            f"/api/v1/jobs/{job_id}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        # Job is reset, not replaced — same ID returned
        assert uuid.UUID(data["job_id"]) == job_id

        # Verify job was reset to pending
        db_session.refresh(job)
        assert job.status == JobStatus.pending
        assert job.last_error is None

    def test_retry_not_found(self, client: TestClient) -> None:
        token = _register_and_login(client)
        fake_id = str(uuid.uuid4())
        resp = client.post(
            f"/api/v1/jobs/{fake_id}/retry",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: File status endpoint
# ---------------------------------------------------------------------------


class TestFileStatusEndpoint:
    """Tests for GET /api/v1/files/{file_id}/status."""

    def test_file_status_pending(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)
        model_file_id = result["model_file_id"]

        resp = client.get(
            f"/api/v1/files/{model_file_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"

    def test_file_status_reflects_job_state(
        self, client: TestClient, db_session: Session
    ) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        result = _upload_glb(client, token, project_id)
        model_file_id = uuid.UUID(result["model_file_id"])

        # Update job to failed
        job = db_session.scalar(
            __import__("sqlalchemy").select(ConversionJob).where(
                ConversionJob.model_file_id == model_file_id
            )
        )
        assert job is not None
        job.status = JobStatus.failed
        job.last_error = "Pipeline error"
        db_session.flush()

        resp = client.get(
            f"/api/v1/files/{model_file_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["lastError"] == "Pipeline error"


# ---------------------------------------------------------------------------
# Tests: Pipeline dispatch (T035)
# ---------------------------------------------------------------------------


class TestPipelineDispatch:
    """Tests for the pipeline dispatch function."""

    def test_dispatch_ifc_returns_callable(self) -> None:
        from app.features.conversion.pipelines.common import dispatch
        fn = dispatch(SourceFormat.ifc)
        assert callable(fn)

    def test_dispatch_dae_returns_callable(self) -> None:
        from app.features.conversion.pipelines.common import dispatch
        fn = dispatch(SourceFormat.dae)
        assert callable(fn)

    def test_dispatch_obj_returns_callable(self) -> None:
        from app.features.conversion.pipelines.common import dispatch
        fn = dispatch(SourceFormat.obj)
        assert callable(fn)

    def test_dispatch_glb_returns_callable(self) -> None:
        from app.features.conversion.pipelines.common import dispatch
        fn = dispatch(SourceFormat.glb)
        assert callable(fn)

    def test_conversion_error_is_exception(self) -> None:
        from app.features.conversion.pipelines.common import ConversionError
        err = ConversionError("test", stage="test_stage")
        assert str(err) == "test"
        assert err.stage == "test_stage"


# ---------------------------------------------------------------------------
# Tests: Conversion service with mocked pipeline
# ---------------------------------------------------------------------------


class TestConversionService:
    """Tests for the conversion service with mocked pipelines."""

    def test_service_marks_job_running_then_ready(
        self, db_session: Session, tmp_path
    ) -> None:
        """Service transitions job: pending → running → ready on success."""
        import tempfile
        from unittest.mock import patch

        from app.features.conversion.service import process_conversion
        from app.features.models.models import ConversionJob

        # Create model file and job
        from app.features.projects.models import Project
        from app.features.auth.models import User

        user = User(
            id=uuid.uuid4(),
            email=f"svc_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
        )
        db_session.add(user)

        project = Project(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Test",
        )
        db_session.add(project)

        model_file = ModelFile(
            id=uuid.uuid4(),
            project_id=project.id,
            uploader_id=user.id,
            original_filename="test.glb",
            source_format=SourceFormat.glb,
            size_bytes=100,
            original_storage_key="originals/test/test.glb",
            content_hash="abc123",
        )
        db_session.add(model_file)

        job = ConversionJob(
            id=uuid.uuid4(),
            model_file_id=model_file.id,
            status=JobStatus.pending,
            attempts=0,
        )
        db_session.add(job)
        db_session.flush()

        # Create a mock GLB file in storage
        from app.core.storage.local_disk import LocalDiskStorage

        storage_root = tmp_path / "storage"
        storage_root.mkdir()
        storage = LocalDiskStorage(str(storage_root))

        # Write the original to storage
        original_key = model_file.original_storage_key
        original_file = tmp_path / "test_input.glb"
        original_file.write_bytes(b"glTF" + b"\x00" * 100)
        storage.put(original_key, original_file, content_type="application/octet-stream")

        # Mock the pipeline to just create a GLB file
        def mock_pipeline(input_path, output_path):
            output_path.write_bytes(b"glTF" + b"\x00" * 200)

        # Mock thumbnail rendering (Blender not available in tests)
        def mock_render_thumbnail(input_path, output_path, size):
            output_path.write_bytes(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 50)

        with (
            patch("app.features.conversion.service.dispatch", return_value=mock_pipeline),
            patch("app.features.conversion.service.render_thumbnail", side_effect=mock_render_thumbnail),
        ):
            process_conversion(
                db_session,
                job_id=job.id,
                model_file_id=model_file.id,
                project_id=project.id,
                source_format=SourceFormat.glb,
                original_storage_key=original_key,
                storage=storage,
            )

        # Refresh and verify
        db_session.refresh(job)
        assert job.status == JobStatus.ready
        assert job.attempts == 1
        assert job.glb_storage_key is not None
        assert job.duration_ms is not None
        assert job.duration_ms >= 0

    def test_service_marks_job_failed_on_pipeline_error(
        self, db_session: Session, tmp_path
    ) -> None:
        """Service transitions job: pending → running → failed on error."""
        from unittest.mock import patch

        from app.features.conversion.service import process_conversion
        from app.features.conversion.pipelines.common import ConversionError

        from app.features.projects.models import Project
        from app.features.auth.models import User

        user = User(
            id=uuid.uuid4(),
            email=f"svc_{uuid.uuid4().hex[:6]}@test.com",
            password_hash="hash",
        )
        db_session.add(user)

        project = Project(
            id=uuid.uuid4(),
            owner_id=user.id,
            name="Test",
        )
        db_session.add(project)

        model_file = ModelFile(
            id=uuid.uuid4(),
            project_id=project.id,
            uploader_id=user.id,
            original_filename="test.glb",
            source_format=SourceFormat.glb,
            size_bytes=100,
            original_storage_key="originals/test/test.glb",
            content_hash="abc123",
        )
        db_session.add(model_file)

        job = ConversionJob(
            id=uuid.uuid4(),
            model_file_id=model_file.id,
            status=JobStatus.pending,
            attempts=0,
        )
        db_session.add(job)
        db_session.flush()

        from app.core.storage.local_disk import LocalDiskStorage
        storage_root = tmp_path / "storage"
        storage_root.mkdir()
        storage = LocalDiskStorage(str(storage_root))

        original_key = model_file.original_storage_key
        original_file = tmp_path / "test_input_fail.glb"
        original_file.write_bytes(b"glTF" + b"\x00" * 100)
        storage.put(original_key, original_file, content_type="application/octet-stream")

        def failing_pipeline(input_path, output_path):
            raise ConversionError("Blender crashed", stage="blender_export")

        with patch("app.features.conversion.service.dispatch", return_value=failing_pipeline):
            process_conversion(
                db_session,
                job_id=job.id,
                model_file_id=model_file.id,
                project_id=project.id,
                source_format=SourceFormat.glb,
                original_storage_key=original_key,
                storage=storage,
            )

        db_session.refresh(job)
        assert job.status == JobStatus.failed
        assert "Blender crashed" in (job.last_error or "")
        assert job.attempts == 1
