"""Integration tests for VS-Projects (T022)."""
from __future__ import annotations

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


class TestCreateProject:
    def test_create_project_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/projects",
            json={"name": "My Project", "description": "A test project"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data

    def test_create_project_no_description(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/projects",
            json={"name": "No Desc Project"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    def test_create_project_empty_name_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/projects",
            json={"name": ""},
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_create_project_whitespace_name_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.post(
            "/api/v1/projects",
            json={"name": "   "},
            headers=_auth_header(token),
        )
        assert resp.status_code == 422

    def test_create_project_no_auth_rejected(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={"name": "Test"})
        assert resp.status_code in (401, 422)


class TestListProjects:
    def test_list_empty(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.get("/api/v1/projects", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["next_cursor"] is None

    def test_list_with_projects(self, client: TestClient) -> None:
        token = _register_and_login(client)
        # Create 3 projects
        for i in range(3):
            client.post(
                "/api/v1/projects",
                json={"name": f"Project {i}"},
                headers=_auth_header(token),
            )
        resp = client.get("/api/v1/projects", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3

    def test_list_excludes_other_users(self, client: TestClient) -> None:
        token1 = _register_and_login(client, "user1@example.com")
        token2 = _register_and_login(client, "user2@example.com")
        client.post(
            "/api/v1/projects",
            json={"name": "User1 Project"},
            headers=_auth_header(token1),
        )
        resp = client.get("/api/v1/projects", headers=_auth_header(token2))
        assert len(resp.json()["items"]) == 0


class TestGetProject:
    def test_get_project_success(self, client: TestClient) -> None:
        token = _register_and_login(client)
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "Test"},
            headers=_auth_header(token),
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test"

    def test_get_project_not_found(self, client: TestClient) -> None:
        token = _register_and_login(client)
        resp = client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            headers=_auth_header(token),
        )
        assert resp.status_code == 404

    def test_get_project_forbidden_other_user(self, client: TestClient) -> None:
        token1 = _register_and_login(client, "owner@example.com")
        token2 = _register_and_login(client, "other@example.com")
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "Private"},
            headers=_auth_header(token1),
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token2))
        assert resp.status_code == 403


class TestUpdateProject:
    def test_update_project_name(self, client: TestClient) -> None:
        token = _register_and_login(client)
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "Old Name"},
            headers=_auth_header(token),
        )
        project_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "New Name"},
            headers=_auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_project_empty_name_rejected(self, client: TestClient) -> None:
        token = _register_and_login(client)
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "Test"},
            headers=_auth_header(token),
        )
        project_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": ""},
            headers=_auth_header(token),
        )
        assert resp.status_code == 422


class TestArchiveProject:
    def test_archive_project(self, client: TestClient) -> None:
        token = _register_and_login(client)
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "To Archive"},
            headers=_auth_header(token),
        )
        project_id = create_resp.json()["id"]
        resp = client.post(f"/api/v1/projects/{project_id}/archive", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is not None

    def test_unarchive_project(self, client: TestClient) -> None:
        token = _register_and_login(client)
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "To Unarchive"},
            headers=_auth_header(token),
        )
        project_id = create_resp.json()["id"]
        client.post(f"/api/v1/projects/{project_id}/archive", headers=_auth_header(token))
        resp = client.post(f"/api/v1/projects/{project_id}/unarchive", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is None


class TestDeleteProject:
    def test_delete_project(self, client: TestClient) -> None:
        token = _register_and_login(client)
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "To Delete"},
            headers=_auth_header(token),
        )
        project_id = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/projects/{project_id}", headers=_auth_header(token))
        assert resp.status_code == 204
        # Verify it's gone
        resp = client.get(f"/api/v1/projects/{project_id}", headers=_auth_header(token))
        assert resp.status_code == 404
