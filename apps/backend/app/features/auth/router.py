"""FastAPI routes for VS-Auth.

Endpoints:
    POST /register  — create account
    POST /login     — authenticate and issue tokens
    POST /refresh   — rotate tokens
    POST /logout    — revoke refresh token
    GET  /me        — return current authenticated user
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security.jwt import InvalidTokenError
from app.features.auth import service
from app.features.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    user = service.register(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
    )
    db.commit()
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, status_code=200)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access, refresh = service.login(db, email=body.email, password=body.password)
    from app.core.config import get_settings

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=get_settings().ACCESS_TOKEN_TTL_S,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=200)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    access, new_refresh = service.refresh(db, raw_token=body.refresh_token)
    from app.core.config import get_settings

    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=get_settings().ACCESS_TOKEN_TTL_S,
    )


@router.post("/logout", response_model=MessageResponse, status_code=200)
def logout(body: RefreshRequest, db: Session = Depends(get_db)) -> MessageResponse:
    service.logout(db, raw_token=body.refresh_token)
    return MessageResponse(message="Logged out.")


@router.get("/me", response_model=UserResponse, status_code=200)
def me(
    authorization: str = Header(..., description="Bearer <token>"),
    db: Session = Depends(get_db),
) -> UserResponse:
    from app.core.errors import UnauthorizedError

    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    token = authorization.removeprefix("Bearer ").strip()
    user = service.get_current_user(db, token=token)
    return UserResponse.model_validate(user)
