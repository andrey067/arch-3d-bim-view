"""Integration tests for Projects — open access."""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestCreateProject:
    def test_create_project_success(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/projects",
            json={"name": "My Project", "description": "A test project"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Project"
        assert data["description"] == "A test project"
        assert "id" in data
        assert "created_at" in data

    def test_create_project_no_description(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={"name": "No Desc Project"})
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    def test_create_project_empty_name_rejected(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={"name": ""})
        assert resp.status_code == 422

    def test_create_project_whitespace_name_rejected(self, client: TestClient) -> None:
        resp = client.post("/api/v1/projects", json={"name": "   "})
        assert resp.status_code == 422


class TestListProjects:
    def test_list_empty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["next_cursor"] is None

    def test_list_with_projects(self, client: TestClient) -> None:
        for i in range(3):
            client.post("/api/v1/projects", json={"name": f"Project {i}"})
        resp = client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3


class TestGetProject:
    def test_get_project_success(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json={"name": "Test"})
        project_id = create_resp.json()["id"]
        resp = client.get(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test"

    def test_get_project_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/v1/projects/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestUpdateProject:
    def test_update_project_name(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json={"name": "Old Name"})
        project_id = create_resp.json()["id"]
        resp = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"name": "New Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_update_project_empty_name_rejected(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json={"name": "Test"})
        project_id = create_resp.json()["id"]
        resp = client.patch(f"/api/v1/projects/{project_id}", json={"name": ""})
        assert resp.status_code == 422


class TestArchiveProject:
    def test_archive_project(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json={"name": "To Archive"})
        project_id = create_resp.json()["id"]
        resp = client.post(f"/api/v1/projects/{project_id}/archive")
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is not None

    def test_unarchive_project(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json={"name": "To Unarchive"})
        project_id = create_resp.json()["id"]
        client.post(f"/api/v1/projects/{project_id}/archive")
        resp = client.post(f"/api/v1/projects/{project_id}/unarchive")
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is None


class TestDeleteProject:
    def test_delete_project(self, client: TestClient) -> None:
        create_resp = client.post("/api/v1/projects", json={"name": "To Delete"})
        project_id = create_resp.json()["id"]
        resp = client.delete(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 204
        resp = client.get(f"/api/v1/projects/{project_id}")
        assert resp.status_code == 404
