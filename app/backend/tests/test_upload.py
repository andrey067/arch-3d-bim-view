"""Integration tests for file upload — open access."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _create_project(client: TestClient, name: str = "Test Project") -> str:
    resp = client.post("/api/v1/projects", json={"name": name})
    return resp.json()["id"]


def _glb_bytes() -> bytes:
    return b"glTF" + b"\x02\x00\x00\x00" + b"\x0c\x00\x00\x00"


def _ifc_bytes() -> bytes:
    return b"ISO-10303-21;\nHEADER;\nENDSEC;\n"


def _dae_bytes() -> bytes:
    return b'<?xml version="1.0"?>\n<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema">\n</COLLADA>'


def _obj_bytes() -> bytes:
    return b"# OBJ file\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n"


def _stl_bytes() -> bytes:
    return b"solid test\nfacet normal 0 0 0\nendfacet\nendsolid test\n"


class TestUploadFile:
    def test_upload_glb_success(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "model_file_id" in data
        assert data["status"] == "pending"

    def test_upload_ifc_success(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.ifc", _ifc_bytes(), "application/octet-stream")},
        )
        assert resp.status_code == 202

    def test_upload_dae_success(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.dae", _dae_bytes(), "application/octet-stream")},
        )
        assert resp.status_code == 202

    def test_upload_obj_success(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.obj", _obj_bytes(), "application/octet-stream")},
        )
        assert resp.status_code == 202

    def test_upload_stl_rejected(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.stl", _stl_bytes(), "application/octet-stream")},
        )
        assert resp.status_code == 415

    def test_upload_empty_file_rejected(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("empty.glb", b"", "model/gltf-binary")},
        )
        assert resp.status_code == 422

    def test_upload_unsupported_format_rejected(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("file.xyz", b"some content", "application/octet-stream")},
        )
        assert resp.status_code == 415

    def test_upload_to_archived_project_rejected(self, client: TestClient) -> None:
        project_id = _create_project(client)
        client.post(f"/api/v1/projects/{project_id}/archive")
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
        )
        assert resp.status_code == 409


class TestListFiles:
    def test_list_empty(self, client: TestClient) -> None:
        project_id = _create_project(client)
        resp = client.get(f"/api/v1/projects/{project_id}/files")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_with_files(self, client: TestClient) -> None:
        project_id = _create_project(client)
        client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model1.glb", _glb_bytes(), "model/gltf-binary")},
        )
        client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model2.ifc", _ifc_bytes(), "application/octet-stream")},
        )
        resp = client.get(f"/api/v1/projects/{project_id}/files")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2


class TestDeleteFile:
    def test_delete_file_success(self, client: TestClient) -> None:
        project_id = _create_project(client)
        upload_resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
        )
        file_id = upload_resp.json()["model_file_id"]
        resp = client.delete(f"/api/v1/files/{file_id}")
        assert resp.status_code == 204
        list_resp = client.get(f"/api/v1/projects/{project_id}/files")
        assert len(list_resp.json()["items"]) == 0

    def test_delete_file_not_found(self, client: TestClient) -> None:
        resp = client.delete("/api/v1/files/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404
