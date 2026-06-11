"""Integration tests for VS-Upload (T023-T025)."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str = "test@example.com", password: str = "password123") -> str:
    """Register a user and return the access token. Handles 409 if user already exists."""
    register_resp = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    # If register fails with 409 (conflict), the user already exists - just login
    if register_resp.status_code == 409:
        pass  # User exists, will login below
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_project(client: TestClient, token: str, name: str = "Test Project") -> str:
    """Create a project and return its ID."""
    resp = client.post(
        "/api/v1/projects",
        json={"name": name},
        headers=_auth_header(token),
    )
    return resp.json()["id"]


def _glb_bytes() -> bytes:
    """Return minimal valid GLB bytes (glTF magic + header)."""
    # Minimal GLB: magic "glTF" + version 2 + length 12
    return b"glTF" + b"\x02\x00\x00\x00" + b"\x0c\x00\x00\x00"


def _ifc_bytes() -> bytes:
    """Return minimal IFC header bytes."""
    return b"ISO-10303-21;\nHEADER;\nENDSEC;\n"


def _dae_bytes() -> bytes:
    """Return minimal COLLADA XML bytes."""
    return b'<?xml version="1.0"?>\n<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema">\n</COLLADA>'


def _obj_bytes() -> bytes:
    """Return minimal OBJ bytes."""
    return b"# OBJ file\nv 0.0 0.0 0.0\nv 1.0 0.0 0.0\nv 0.0 1.0 0.0\nf 1 2 3\n"


def _stl_bytes() -> bytes:
    """Return STL text bytes (should be rejected)."""
    return b"solid test\nfacet normal 0 0 0\nendfacet\nendsolid test\n"


class TestUploadFile:
    def test_upload_glb_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "model_file_id" in data
        assert data["status"] == "pending"

    def test_upload_ifc_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.ifc", _ifc_bytes(), "application/octet-stream")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 202

    def test_upload_dae_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.dae", _dae_bytes(), "application/octet-stream")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 202

    def test_upload_obj_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.obj", _obj_bytes(), "application/octet-stream")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 202

    def test_upload_stl_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.stl", _stl_bytes(), "application/octet-stream")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 415

    def test_upload_empty_file_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("empty.glb", b"", "model/gltf-binary")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_upload_unsupported_format_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("file.xyz", b"some content", "application/octet-stream")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 415

    def test_upload_no_auth_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
        )
        assert resp.status_code in (401, 422)

    def test_upload_to_archived_project_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        # Archive the project
        client.post(f"/api/v1/projects/{project_id}/archive", headers=_auth_header(token))
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
            headers=_auth_header(token),
        )
        assert resp.status_code == 409

    def test_upload_to_other_user_project_rejected(self, client: TestClient) -> None:
        token1 = _register_and_login(client, "owner@example.com")
        token2 = _register_and_login(client, "other@example.com")
        project_id = _create_project(client, token1)
        resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
            headers=_auth_header(token2),
        )
        assert resp.status_code == 403


class TestListFiles:
    def test_list_empty(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        resp = client.get(f"/api/v1/projects/{project_id}/files", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_list_with_files(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        # Upload 2 files
        client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model1.glb", _glb_bytes(), "model/gltf-binary")},
            headers=_auth_header(token),
        )
        client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model2.ifc", _ifc_bytes(), "application/octet-stream")},
            headers=_auth_header(token),
        )
        resp = client.get(f"/api/v1/projects/{project_id}/files", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2

    def test_list_forbidden_other_user(self, client: TestClient) -> None:
        token1 = _register_and_login(client, "owner@example.com")
        token2 = _register_and_login(client, "other@example.com")
        project_id = _create_project(client, token1)
        resp = client.get(f"/api/v1/projects/{project_id}/files", headers=_auth_header(token2))
        assert resp.status_code == 403


class TestDeleteFile:
    def test_delete_file_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        project_id = _create_project(client, token)
        upload_resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
            headers=_auth_header(token),
        )
        file_id = upload_resp.json()["model_file_id"]
        resp = client.delete(f"/api/v1/files/{file_id}", headers=_auth_header(token))
        assert resp.status_code == 204
        # Verify it's gone
        list_resp = client.get(f"/api/v1/projects/{project_id}/files", headers=_auth_header(token))
        assert len(list_resp.json()["items"]) == 0

    def test_delete_file_not_found(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.delete(
            "/api/v1/files/00000000-0000-0000-0000-000000000000",
            headers=_auth_header(token),
        )
        assert resp.status_code == 404

    def test_delete_file_forbidden_other_user(self, client: TestClient) -> None:
        token1 = _register_and_login(client, "owner@example.com")
        token2 = _register_and_login(client, "other@example.com")
        project_id = _create_project(client, token1)
        upload_resp = client.post(
            f"/api/v1/projects/{project_id}/files",
            files={"file": ("model.glb", _glb_bytes(), "model/gltf-binary")},
            headers=_auth_header(token1),
        )
        file_id = upload_resp.json()["model_file_id"]
        resp = client.delete(f"/api/v1/files/{file_id}", headers=_auth_header(token2))
        assert resp.status_code == 403
