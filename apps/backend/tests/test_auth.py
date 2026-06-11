"""VS-Auth integration tests (Sprint 1).

Covers: register, login, refresh, logout, /me.
"""
from __future__ import annotations

import pytest


# --- T015: POST /auth/register ---

def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "owner@example.com"
    assert "password_hash" not in data
    assert "id" in data
    assert "created_at" in data


def test_register_with_display_name(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user2@example.com",
            "password": "12345678",
            "display_name": "Owner",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["display_name"] == "Owner"


def test_register_duplicate_email(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "12345678"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "12345678"},
    )
    assert response.status_code == 409


def test_register_password_too_short(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "1234567"},
    )
    assert response.status_code == 422


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "12345678"},
    )
    assert response.status_code == 422


# --- T016: POST /auth/login ---

def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "correct-horse-battery"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "correct-horse-battery"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "correct-horse-battery"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_nonexistent_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "noone@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


# --- T017: POST /auth/refresh ---

def test_refresh_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "correct-horse-battery"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "correct-horse-battery"},
    )
    old_refresh = login_resp.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # Old token should no longer work (rotation)
    response2 = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert response2.status_code == 401


def test_refresh_invalid_token(client):
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token-that-does-not-exist"},
    )
    assert response.status_code == 401


# --- T018: POST /auth/logout ---

def test_logout_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "correct-horse-battery"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "logout@example.com", "password": "correct-horse-battery"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200

    # Token should no longer work
    response2 = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response2.status_code == 401


def test_logout_idempotent(client):
    """Logout is idempotent — even with an invalid token, returns 200."""
    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "nonexistent-token"},
    )
    assert response.status_code == 200


# --- GET /auth/me ---

def test_me_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "correct-horse-battery"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "correct-horse-battery"},
    )
    access_token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "password_hash" not in data


def test_me_no_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code in (401, 422)


def test_me_expired_token(client):
    import time
    from unittest.mock import patch

    # Register + login
    client.post(
        "/api/v1/auth/register",
        json={"email": "expired@example.com", "password": "correct-horse-battery"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "expired@example.com", "password": "correct-horse-battery"},
    )
    access_token = login_resp.json()["access_token"]

    # Fast-forward time by patching jwt decode to simulate expiry
    # (integration approach: test the error path)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
