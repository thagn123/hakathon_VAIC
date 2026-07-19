"""Local login endpoint for the dashboard demo."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import issue_session_token
from app.config import settings
from app.integrations.enterprise import SQLiteSSOAdapter
from app.integrations.pg import PostgresSSOAdapter
from app.integrations.errors import ContextError


def _sso_adapter():
    return PostgresSSOAdapter() if settings.DATABASE_URL else SQLiteSSOAdapter()


router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    employee_id: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    employee_id: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, x_session_id: Optional[str] = Header(None)) -> LoginResponse:
    # Demo password is deliberately configured outside source control. In a
    # real deployment this endpoint must be replaced by the enterprise SSO.
    if not settings.DEMO_AUTH_ENABLED or body.password != settings.DEMO_LOGIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_CREDENTIALS", "message": "Sai tai khoan hoac mat khau."})
    try:
        identity = _sso_adapter().get_employee_identity(body.employee_id.upper(), correlation_id=f"TRACE-{uuid.uuid4().hex.upper()}")
    except ContextError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_CREDENTIALS", "message": "Sai tai khoan hoac mat khau."})
    token_ttl = settings.AUTH_TOKEN_TTL_SECONDS
    return LoginResponse(
        access_token=issue_session_token(identity["employee_id"], ttl_seconds=token_ttl),
        expires_in=token_ttl,
        employee_id=identity["employee_id"],
    )
