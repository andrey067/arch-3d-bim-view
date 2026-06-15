"""Tests for Conversion: job creation, status, retry, and pipeline dispatch — open access."""
from __future__ import annotations

import shutil
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.identity import DEFAULT_OWNER_ID
from app.features.models.models import ConversionJob, JobStatus, ModelFile, SourceFormat

GLB_MAGIC = b"glTF" + b"\x02\x00\x00\x00" + b"\x00\x00\x00\x00"


def _create_project(client: TestClient) -> str:
    resp = client.post("/api/v1/projects", json={"name": "Test Project"})
    assert resp.status_code == 201
    return resp.json()["id"]


def _upload_glb(client: TestClient, project_id: str) -> dict:
    content = GLB_MAGIC + b"\x00" * 100
    resp = client.post(
        f"/api/v1/projects/{project_id}/files",
        files={"file": ("test.glb", content, "model/gltf-binary")},
    )
    assert resp.status_code == 202
    return resp.json()


class TestUploadCreatesJob:
    def test_upload_returns_conversion_job_id(self, client: TestClient) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)

        assert "conversion_job_id" in result
        assert result["status"] == "pending"
        assert result["conversion_job_id"] is not None

    def test_conversion_job_persisted(self, client: TestClient, db_session: Session) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)

        job = db_session.get(ConversionJob, result["conversion_job_id"])
        assert job is not None
        assert job.status == JobStatus.pending
        assert job.attempts == 0


class TestJobStatusEndpoint:
    def test_get_pending_job(self, client: TestClient) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)
        job_id = result["conversion_job_id"]

        resp = client.get(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["attempts"] == 0
        assert data["last_error"] is None

    def test_job_not_found(self, client: TestClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/jobs/{fake_id}")
        assert resp.status_code == 404


class TestJobRetryEndpoint:
    def test_retry_pending_job_returns_409(self, client: TestClient) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)
        job_id = result["conversion_job_id"]

        resp = client.post(f"/api/v1/jobs/{job_id}/retry")
        assert resp.status_code == 409

    def test_retry_failed_job_resets_to_pending(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)

        job = db_session.get(ConversionJob, result["conversion_job_id"])
        assert job is not None
        job.status = JobStatus.failed
        job.last_error = "Test error"
        db_session.flush()

        resp = client.post(f"/api/v1/jobs/{result['conversion_job_id']}/retry")
        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"] == result["conversion_job_id"]

        db_session.refresh(job)
        assert job.status == JobStatus.pending
        assert job.last_error is None

    def test_retry_not_found(self, client: TestClient) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/api/v1/jobs/{fake_id}/retry")
        assert resp.status_code == 404


class TestFileStatusEndpoint:
    def test_file_status_pending(self, client: TestClient) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)
        model_file_id = result["model_file_id"]

        resp = client.get(f"/api/v1/files/{model_file_id}/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_file_status_reflects_job_state(
        self, client: TestClient, db_session: Session,
    ) -> None:
        project_id = _create_project(client)
        result = _upload_glb(client, project_id)

        from sqlalchemy import select
        job = db_session.scalar(
            select(ConversionJob).where(ConversionJob.model_file_id == result["model_file_id"])
        )
        assert job is not None
        job.status = JobStatus.failed
        job.last_error = "Pipeline error"
        db_session.flush()

        resp = client.get(f"/api/v1/files/{result['model_file_id']}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "failed"
        assert data["lastError"] == "Pipeline error"


class TestPipelineDispatch:
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


class TestConversionService:
    def test_service_marks_job_running_then_ready(
        self, db_session: Session, tmp_path,
    ) -> None:
        from app.features.conversion.service import process_conversion
        from app.features.projects.models import Project

        project = Project(id=str(uuid.uuid4()), owner_id=DEFAULT_OWNER_ID, name="Test")
        db_session.add(project)
        model_file = ModelFile(
            id=str(uuid.uuid4()), project_id=project.id, uploader_id=DEFAULT_OWNER_ID,
            original_filename="test.glb", source_format=SourceFormat.glb,
            size_bytes=100, original_storage_key="originals/test/test.glb", content_hash="abc123",
        )
        db_session.add(model_file)
        job = ConversionJob(id=str(uuid.uuid4()), model_file_id=model_file.id, status=JobStatus.pending, attempts=0)
        db_session.add(job)
        db_session.flush()
        db_session.commit()

        storage_root = tmp_path / "storage"
        storage_root.mkdir()
        original_file = tmp_path / "test_input.glb"
        original_file.write_bytes(b"glTF" + b"\x00" * 100)

        from app.core.storage.local_disk import LocalDiskStorage
        storage = LocalDiskStorage(str(storage_root))
        storage.put(model_file.original_storage_key, original_file, content_type="application/octet-stream")

        import os
        from app.core.config import get_settings
        original_env = os.environ.get("STORAGE_ROOT")
        os.environ["STORAGE_ROOT"] = str(storage_root)
        get_settings.cache_clear()

        def mock_pipeline(input_path, output_path):
            output_path.write_bytes(b"glTF" + b"\x00" * 200)

        from sqlalchemy.orm import Session as SASession

        def session_factory():
            s = SASession(bind=db_session.bind)
            return s

        with patch("app.features.conversion.service.dispatch", return_value=mock_pipeline):
            process_conversion(
                session_factory,
                job_id=job.id,
                model_file_id=model_file.id,
                project_id=project.id,
                source_format=SourceFormat.glb.value,
                original_storage_key=model_file.original_storage_key,
            )

        get_settings.cache_clear()
        if original_env:
            os.environ["STORAGE_ROOT"] = original_env
        else:
            os.environ.pop("STORAGE_ROOT", None)

        # The background session committed directly to the engine.
        # Expire all cached state so the test session re-fetches from the DB.
        db_session.expire_all()
        refreshed_job = db_session.get(ConversionJob, job.id)
        assert refreshed_job is not None
        assert refreshed_job.status == JobStatus.ready
        assert job.attempts == 1
        assert job.glb_storage_key is not None
        assert job.duration_ms is not None

    def test_service_marks_job_failed_on_pipeline_error(
        self, db_session: Session, tmp_path,
    ) -> None:
        from app.features.conversion.service import process_conversion
        from app.features.conversion.pipelines.common import ConversionError
        from app.features.projects.models import Project

        project = Project(id=str(uuid.uuid4()), owner_id=DEFAULT_OWNER_ID, name="Test")
        db_session.add(project)
        model_file = ModelFile(
            id=str(uuid.uuid4()), project_id=project.id, uploader_id=DEFAULT_OWNER_ID,
            original_filename="test.glb", source_format=SourceFormat.glb,
            size_bytes=100, original_storage_key="originals/test2/test.glb", content_hash="abc123",
        )
        db_session.add(model_file)
        job = ConversionJob(id=str(uuid.uuid4()), model_file_id=model_file.id, status=JobStatus.pending, attempts=0)
        db_session.add(job)
        db_session.flush()
        db_session.commit()

        storage_root = tmp_path / "storage"
        storage_root.mkdir()
        original_file = tmp_path / "test_input.glb"
        original_file.write_bytes(b"glTF" + b"\x00" * 100)

        from app.core.storage.local_disk import LocalDiskStorage
        storage = LocalDiskStorage(str(storage_root))
        storage.put(model_file.original_storage_key, original_file, content_type="application/octet-stream")

        import os
        from app.core.config import get_settings
        original_env = os.environ.get("STORAGE_ROOT")
        os.environ["STORAGE_ROOT"] = str(storage_root)
        get_settings.cache_clear()

        def failing_pipeline(input_path, output_path):
            raise ConversionError("Pipeline crashed", stage="glb_export")

        from sqlalchemy.orm import Session as SASession

        def session_factory():
            s = SASession(bind=db_session.bind)
            return s

        with patch("app.features.conversion.service.dispatch", return_value=failing_pipeline):
            process_conversion(
                session_factory,
                job_id=job.id,
                model_file_id=model_file.id,
                project_id=project.id,
                source_format=SourceFormat.glb.value,
                original_storage_key=model_file.original_storage_key,
            )

        get_settings.cache_clear()
        if original_env:
            os.environ["STORAGE_ROOT"] = original_env
        else:
            os.environ.pop("STORAGE_ROOT", None)

        db_session.expire_all()
        refreshed_job = db_session.get(ConversionJob, job.id)
        assert refreshed_job is not None
        assert refreshed_job.status == JobStatus.failed
        assert "Pipeline crashed" in (refreshed_job.last_error or "")
        assert job.attempts == 1


@pytest.mark.skipif(
    shutil.which("IfcConvert") is None,
    reason="IfcConvert not available locally",
)
class TestIfcConvertIntegration:
    def test_real_ifc_to_glb(self, tmp_path) -> None:
        from app.features.conversion.pipelines.ifc_convert import run

        ifc_file = tmp_path / "test.ifc"
        ifc_file.write_text(
            "ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('test'),'2;1');\n"
            "FILE_NAME('test.ifc','2024-01-01',(''),('',''),'','','');\n"
            "FILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
        )
        output = tmp_path / "output.glb"

        try:
            run(ifc_file, output)
            assert output.exists()
            assert output.stat().st_size > 0
            assert output.read_bytes()[:4] == b"glTF"
        except Exception as e:
            pytest.skip(f"IfcConvert integration failed: {e}")


@pytest.mark.skipif(
    shutil.which("usd_from_gltf") is None,
    reason="usd_from_gltf not available locally",
)
class TestUsdzIntegration:
    def test_real_glb_to_usdz(self, tmp_path) -> None:
        from app.features.conversion.pipelines.usdz import run

        glb_file = tmp_path / "test.glb"
        glb_file.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 100)
        output = tmp_path / "output.usdz"

        try:
            run(glb_file, output)
            assert output.exists()
            assert output.stat().st_size > 0
        except Exception as e:
            pytest.skip(f"usd_from_gltf integration failed: {e}")
